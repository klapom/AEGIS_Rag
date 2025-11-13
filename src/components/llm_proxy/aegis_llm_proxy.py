"""
AegisRAG LLM Proxy using Mozilla ANY-LLM.

This module provides a thin wrapper around Mozilla's ANY-LLM framework,
adding AegisRAG-specific routing logic while leveraging ANY-LLM's
multi-provider abstraction, budget management, and fallback mechanisms.

Sprint Context: Sprint 23 (2025-11-13) - Feature 23.4
Related ADR: ADR-033 (Mozilla ANY-LLM Integration)

Architecture:
    User → AegisLLMProxy (routing) → ANY-LLM (execution) → Providers

Responsibilities:
    AegisLLMProxy:
        - Data privacy enforcement (PII/HIPAA → local only)
        - Quality-based routing (critical → OpenAI)
        - Complexity-based routing (high → Ollama Cloud)
        - Default routing (simple → local)
        - Metrics tracking (Prometheus, LangSmith)

    ANY-LLM:
        - Multi-provider abstraction
        - Budget management and enforcement
        - Connection pooling
        - Automatic fallback (provider → provider → local)
"""

import time

import structlog
from any_llm import LLMProvider, acompletion

from src.components.llm_proxy.config import LLMProxyConfig, get_llm_proxy_config
from src.components.llm_proxy.cost_tracker import CostTracker
from src.components.llm_proxy.models import (
    Complexity,
    DataClassification,
    LLMResponse,
    LLMTask,
    QualityRequirement,
    TaskType,
)
from src.core.exceptions import LLMExecutionError

logger = structlog.get_logger(__name__)


class AegisLLMProxy:
    """
    AegisRAG-specific LLM proxy with intelligent routing.

    This proxy adds AegisRAG-specific routing logic on top of Mozilla ANY-LLM,
    enabling three-tier execution (Local → Ollama Cloud → OpenAI) with
    data privacy enforcement and cost optimization.

    Three-Tier Strategy (ADR-033):
        TIER 1: Local Ollama (FREE, 70% tasks)
            - Embeddings (always local)
            - Simple queries
            - Sensitive data (PII/HIPAA)

        TIER 2: Ollama Cloud ($0.001/1k tokens, 20% tasks)
            - Standard extraction
            - Batch processing (>10 docs)
            - High quality + medium complexity

        TIER 3: OpenAI API ($0.015/1k tokens, 10% tasks)
            - Critical quality (legal, medical)
            - Very high complexity
            - Complex reasoning

    Example:
        proxy = get_aegis_llm_proxy()

        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract entities from legal contract...",
            quality_requirement=QualityRequirement.CRITICAL,
        )

        response = await proxy.generate(task)
        print(f"Provider: {response.provider}, Cost: ${response.cost_usd}")
    """

    def __init__(self, config: LLMProxyConfig | None = None):
        """
        Initialize AegisLLMProxy with configuration.

        Args:
            config: Configuration for providers, budgets, routing.
                    If None, loads from config/llm_config.yml + environment.

        Raises:
            ValueError: If configuration is invalid or required providers missing
        """
        self.config = config or get_llm_proxy_config()

        # Validate required provider (local_ollama)
        if not self.config.is_provider_enabled("local_ollama"):
            raise ValueError("local_ollama provider is required but not configured")

        # Initialize persistent cost tracker (SQLite)
        self.cost_tracker = CostTracker()

        # Track budgets (simplified - no ANY-LLM BudgetManager needed)
        # Load current month spending from DB
        self._monthly_spending = self.cost_tracker.get_monthly_spending()
        if "alibaba_cloud" not in self._monthly_spending:
            self._monthly_spending["alibaba_cloud"] = 0.0
        if "openai" not in self._monthly_spending:
            self._monthly_spending["openai"] = 0.0

        # Track metrics
        self._request_count = 0
        self._total_cost = 0.0

        logger.info(
            "aegis_llm_proxy_initialized",
            providers=list(self.config.providers.keys()),
            budgets=self.config.budgets.get("monthly_limits", {}),
            current_spending=self._monthly_spending,
        )

    def _is_budget_exceeded(self, provider: str) -> bool:
        """
        Check if budget is exceeded for provider.

        Args:
            provider: Provider name (alibaba_cloud or openai)

        Returns:
            True if budget exceeded
        """
        if provider == "local_ollama":
            return False  # Local is always free

        limit = self.config.get_budget_limit(provider)
        if limit == 0.0:
            return False  # No limit configured

        spent = self._monthly_spending.get(provider, 0.0)
        return spent >= limit

    async def generate(
        self,
        task: LLMTask,
        stream: bool = False,
    ) -> LLMResponse:
        """
        Generate LLM response with intelligent routing.

        This is the main entry point for all LLM generation requests.
        It handles routing, execution, fallback, and metrics tracking.

        Args:
            task: LLM task with prompt, quality requirements, data classification
            stream: Enable streaming response (token-by-token)

        Returns:
            LLMResponse with content, provider used, cost, latency

        Raises:
            LLMExecutionError: If all providers fail

        Example:
            task = LLMTask(
                task_type=TaskType.EXTRACTION,
                prompt="Extract entities...",
                quality_requirement=QualityRequirement.HIGH,
            )
            response = await proxy.generate(task)
        """
        start_time = time.time()

        # Step 1: AEGIS ROUTING LOGIC (custom)
        provider, reason = self._route_task(task)

        logger.info(
            "routing_decision",
            task_id=str(task.id),
            task_type=task.task_type,
            provider=provider,
            reason=reason,
            quality=task.quality_requirement,
            complexity=task.complexity,
        )

        # Step 2: ANY-LLM EXECUTION
        try:
            result = await self._execute_with_any_llm(
                provider=provider,
                task=task,
                stream=stream,
            )

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            result.latency_ms = latency_ms
            result.routing_reason = reason

            # Step 3: AEGIS METRICS (custom)
            self._track_metrics(provider, task, result)

            return result

        except Exception as e:
            # Provider error → try local as last resort
            logger.error(
                "provider_error_fallback",
                provider=provider,
                error=str(e),
                fallback="local_ollama",
                task_id=str(task.id),
            )

            try:
                result = await self._execute_with_any_llm(
                    provider="local_ollama",
                    task=task,
                    stream=stream,
                )
                result.fallback_used = True
                result.routing_reason = f"provider_error_{provider}"
                latency_ms = (time.time() - start_time) * 1000
                result.latency_ms = latency_ms
                return result

            except Exception as local_error:
                # Even local failed → raise error
                logger.critical(
                    "all_providers_failed",
                    task_id=str(task.id),
                    last_provider=provider,
                    local_error=str(local_error),
                )
                raise LLMExecutionError(
                    f"All LLM providers failed for task {task.id}"
                ) from local_error

    def _route_task(self, task: LLMTask) -> tuple[str, str]:
        """
        Route task to optimal provider (AEGIS CUSTOM LOGIC).

        Routing Priority:
            1. Data Privacy: PII/HIPAA/Confidential → ALWAYS local
            2. Task Type: Embeddings → ALWAYS local
            3. Budget Check: If exceeded → Local
            4. Quality + Complexity: Critical + High → OpenAI
            5. Quality or Batch: High quality OR batch → Ollama Cloud
            6. Default: Local (70% of tasks)

        Args:
            task: LLM task with routing criteria

        Returns:
            (provider_name, routing_reason) tuple

        Example:
            provider, reason = self._route_task(task)
            # → ("local_ollama", "sensitive_data_local_only")
        """
        # PRIORITY 1: Data Privacy (PII/HIPAA always local)
        sensitive_classifications = [
            DataClassification.PII,
            DataClassification.HIPAA,
            DataClassification.CONFIDENTIAL,
        ]
        if task.data_classification in sensitive_classifications:
            logger.info(
                "routing_data_privacy",
                classification=task.data_classification,
                provider="local_ollama",
            )
            return ("local_ollama", "sensitive_data_local_only")

        # PRIORITY 2: Task Type (embeddings always local)
        if task.task_type == TaskType.EMBEDDING:
            return ("local_ollama", "embeddings_local_only")

        # PRIORITY 2.5: Vision tasks (VLM) - Prefer Alibaba Cloud Qwen3-VL-30B
        if task.task_type == TaskType.VISION:
            if self.config.is_provider_enabled("alibaba_cloud"):
                return ("alibaba_cloud", "vision_task_best_vlm")
            # Fallback to local VLM if cloud unavailable
            return ("local_ollama", "vision_task_local_fallback")

        # PRIORITY 3: TIER 3 (OpenAI) - Critical quality + High complexity
        if (
            self.config.is_provider_enabled("openai")
            and task.quality_requirement == QualityRequirement.CRITICAL
            and task.complexity in [Complexity.HIGH, Complexity.VERY_HIGH]
        ):
            # Check if OpenAI budget not exceeded
            if not self._is_budget_exceeded("openai"):
                return ("openai", "critical_quality_high_complexity")
            else:
                logger.warning("budget_exceeded", provider="openai", fallback="alibaba_cloud_or_local")

        # PRIORITY 4: TIER 2 (Alibaba Cloud / Qwen) - High quality OR batch processing
        if self.config.is_provider_enabled("alibaba_cloud"):
            # High quality + high complexity
            if (
                task.quality_requirement == QualityRequirement.HIGH
                and task.complexity == Complexity.HIGH
            ):
                if not self._is_budget_exceeded("alibaba_cloud"):
                    return ("alibaba_cloud", "high_quality_high_complexity")

            # Batch processing (>10 documents)
            if task.batch_size and task.batch_size > 10:
                if not self._is_budget_exceeded("alibaba_cloud"):
                    return ("alibaba_cloud", "batch_processing")

        # DEFAULT: TIER 1 (Local) - 70% of tasks
        return ("local_ollama", "default_local")

    async def _execute_with_any_llm(
        self,
        provider: str,
        task: LLMTask,
        stream: bool,
    ) -> LLMResponse:
        """
        Execute task with ANY-LLM acompletion function.

        ANY-LLM responsibilities:
            - Convert to provider-specific API format
            - Handle connection pooling
            - Automatic retry on transient errors

        Args:
            provider: Provider name (local_ollama, alibaba_cloud, openai)
            task: LLM task
            stream: Enable streaming

        Returns:
            LLMResponse with generated content and metadata

        Raises:
            Exception: If provider execution fails
        """
        model = self._get_model_for_provider(provider, task)

        # Map internal provider name to LLMProvider enum
        provider_map = {
            "local_ollama": LLMProvider.OLLAMA,
            "alibaba_cloud": LLMProvider.OPENAI,  # Alibaba DashScope uses OpenAI-compatible API
            "openai": LLMProvider.OPENAI,
        }

        # Get provider-specific configuration
        provider_config = self.config.providers.get(provider, {})

        # Determine api_base and api_key for providers
        api_base = None
        api_key = None

        if provider == "local_ollama":
            api_base = provider_config.get("base_url")
        elif provider in ["alibaba_cloud", "openai"]:
            api_base = provider_config.get("base_url")
            api_key = provider_config.get("api_key")

        messages = [{"role": "user", "content": task.prompt}]

        # Call ANY-LLM acompletion function
        response = await acompletion(
            model=model,
            messages=messages,
            provider=provider_map[provider],
            api_base=api_base,
            api_key=api_key,
            max_tokens=task.max_tokens,
            temperature=task.temperature,
            stream=stream,
        )

        # Convert ANY-LLM response to AegisRAG format
        # Extract token breakdown for accurate cost calculation
        tokens_input = 0
        tokens_output = 0
        tokens_used = 0

        if hasattr(response, "usage") and response.usage:
            tokens_input = getattr(response.usage, "prompt_tokens", 0) or 0
            tokens_output = getattr(response.usage, "completion_tokens", 0) or 0
            tokens_used = getattr(response.usage, "total_tokens", 0) or 0

        # Track spending for cloud providers with accurate input/output split
        cost = self._calculate_cost(
            provider=provider,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            tokens_total=tokens_used,
        )
        if provider in self._monthly_spending:
            self._monthly_spending[provider] += cost

        return LLMResponse(
            content=response.choices[0].message.content,
            provider=provider,
            model=model,
            tokens_used=tokens_used,
            cost_usd=cost,
        )

    def _get_model_for_provider(self, provider: str, task: LLMTask) -> str:
        """
        Get optimal model for provider and task.

        Args:
            provider: Provider name
            task: LLM task (may contain model preferences)

        Returns:
            Model name

        Example:
            model = self._get_model_for_provider("openai", task)
            # → "gpt-4o" (if task.quality_requirement == CRITICAL)
        """
        # Check task-specific model preference
        if provider == "local_ollama" and task.model_local:
            return task.model_local
        if provider == "alibaba_cloud" and task.model_cloud:
            return task.model_cloud
        if provider == "openai" and task.model_openai:
            return task.model_openai

        # Use config defaults based on task type
        default_model = self.config.get_default_model(provider, task.task_type)
        if default_model:
            return default_model

        # Fallback to hardcoded defaults
        default_models = {
            "local_ollama": "hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q4_K_M",
            "alibaba_cloud": "qwen3-32b",
            "openai": "gpt-4o",
        }
        return default_models.get(provider, "hf.co/MaziyarPanahi/gemma-3-4b-it-GGUF:Q4_K_M")

    def _calculate_cost(
        self,
        provider: str,
        tokens_input: int = 0,
        tokens_output: int = 0,
        tokens_total: int = 0,
    ) -> float:
        """
        Calculate cost for request (USD) with accurate input/output split.

        Pricing (as of 2025-11-13, International Singapore region):
            - Local Ollama: FREE
            - Alibaba Cloud qwen-turbo: $0.05/M input, $0.2/M output
            - Alibaba Cloud qwen-plus: $0.4/M input, $1.2/M output
            - Alibaba Cloud qwen-max: $1.6/M input, $6.4/M output
            - OpenAI GPT-4o: $2.50/M input, $10.00/M output

        Args:
            provider: Provider name
            tokens_input: Input tokens (prompt)
            tokens_output: Output tokens (completion)
            tokens_total: Total tokens (fallback if input/output unavailable)

        Returns:
            Cost in USD
        """
        # If input/output not available, use total tokens (old behavior)
        if tokens_input == 0 and tokens_output == 0 and tokens_total > 0:
            # Use legacy pricing (average input+output rate)
            pricing_legacy = {
                "local_ollama": 0.0,  # Free
                "alibaba_cloud": 0.000125,  # avg of $0.05/$0.2 per 1M = $0.125/1M
                "openai": 0.00625,  # avg of $2.50/$10.00 per 1M = $6.25/1M
            }
            cost = (tokens_total / 1_000_000) * pricing_legacy.get(provider, 0.0)
        else:
            # Use accurate input/output pricing
            pricing = {
                "local_ollama": {"input": 0.0, "output": 0.0},  # Free
                "alibaba_cloud": {
                    "input": 0.05,  # $0.05 per 1M tokens (qwen-turbo)
                    "output": 0.2,  # $0.2 per 1M tokens (qwen-turbo)
                },
                "openai": {
                    "input": 2.50,  # $2.50 per 1M tokens (gpt-4o)
                    "output": 10.00,  # $10.00 per 1M tokens (gpt-4o)
                },
            }

            provider_pricing = pricing.get(provider, {"input": 0.0, "output": 0.0})
            cost = (
                (tokens_input / 1_000_000) * provider_pricing["input"]
                + (tokens_output / 1_000_000) * provider_pricing["output"]
            )

        # Track total cost
        self._total_cost += cost

        return cost

    def _track_metrics(self, provider: str, task: LLMTask, result: LLMResponse):
        """
        Track metrics for observability (Prometheus, LangSmith, SQLite).

        Metrics tracked:
            - SQLite persistent storage (per-request details)
            - llm_requests_total (counter, by provider/task_type)
            - llm_latency_seconds (histogram, by provider)
            - llm_cost_usd (gauge, by provider)
            - llm_tokens_used (counter, by provider)

        Args:
            provider: Provider used
            task: Original task
            result: Response with metrics
        """
        self._request_count += 1

        # Log structured metrics
        logger.info(
            "llm_request_complete",
            task_id=str(task.id),
            provider=provider,
            model=result.model,
            task_type=task.task_type,
            tokens_used=result.tokens_used,
            cost_usd=result.cost_usd,
            latency_ms=result.latency_ms,
            routing_reason=result.routing_reason,
            fallback_used=result.fallback_used,
        )

        # Persist to SQLite database (Sprint 23 - persistent cost tracking)
        try:
            # TD-24.1: Token breakdown is already in result.tokens_used (total)
            # TODO: Extract input/output split when available from result metadata
            # For now, estimate 50/50 split (will be improved in Sprint 25)
            tokens_input = result.tokens_used // 2
            tokens_output = result.tokens_used - tokens_input

            self.cost_tracker.track_request(
                provider=provider,
                model=result.model,
                task_type=task.task_type,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_usd=result.cost_usd,
                latency_ms=result.latency_ms,
                routing_reason=result.routing_reason,
                fallback_used=result.fallback_used,
                task_id=str(task.id),
            )
        except Exception as e:
            logger.warning("Failed to persist cost tracking", error=str(e))

        # Prometheus metrics (Sprint 24 Feature 24.1)
        try:
            from src.core.metrics import track_llm_request, update_budget_metrics

            # Track request metrics
            track_llm_request(
                provider=provider,
                model=result.model,
                task_type=task.task_type,
                tokens_used=result.tokens_used,
                cost_usd=result.cost_usd,
                latency_seconds=result.latency_ms / 1000.0,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
            )

            # Update budget metrics for cloud providers
            if provider in ["alibaba_cloud", "openai"]:
                budget_limit = self.config.get_budget_limit(provider)
                monthly_spending = self._monthly_spending.get(provider, 0.0)
                update_budget_metrics(provider, monthly_spending, budget_limit)

        except ImportError:
            logger.warning("Prometheus metrics not available (metrics module not found)")
        except Exception as e:
            logger.warning("Failed to track Prometheus metrics", error=str(e))

    def get_metrics_summary(self) -> dict:
        """
        Get summary of proxy metrics.

        Returns:
            Dict with request count, total cost, etc.

        Example:
            summary = proxy.get_metrics_summary()
            print(f"Total requests: {summary['request_count']}")
            print(f"Total cost: ${summary['total_cost_usd']:.2f}")
        """
        return {
            "request_count": self._request_count,
            "total_cost_usd": self._total_cost,
            "providers_enabled": list(self.config.providers.keys()),
        }


# Singleton instance (lazy initialization)
_proxy_instance: AegisLLMProxy | None = None


def get_aegis_llm_proxy(config: LLMProxyConfig | None = None) -> AegisLLMProxy:
    """
    Get singleton instance of AegisLLMProxy.

    This function caches the proxy instance to avoid re-initialization
    of ANY-LLM providers on every call.

    Args:
        config: Optional configuration (for testing)

    Returns:
        AegisLLMProxy instance

    Example:
        from src.components.llm_proxy import get_aegis_llm_proxy, LLMTask

        proxy = get_aegis_llm_proxy()
        response = await proxy.generate(task)
    """
    global _proxy_instance

    # If config provided, create new instance (for testing)
    if config is not None:
        return AegisLLMProxy(config=config)

    # Otherwise use singleton
    if _proxy_instance is None:
        _proxy_instance = AegisLLMProxy()

    return _proxy_instance
