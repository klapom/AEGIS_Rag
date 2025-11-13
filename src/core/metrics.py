"""Prometheus Metrics for LLM Cost Tracking.

Sprint 24 - Feature 24.1: Prometheus Metrics Implementation
Related ADR: ADR-033 (Multi-Cloud LLM Execution)

This module provides Prometheus metrics for monitoring LLM usage, cost tracking,
and performance across multiple providers (Local Ollama, Alibaba Cloud, OpenAI).

Metrics Exported:
- llm_requests_total: Total number of LLM requests (counter)
- llm_latency_seconds: LLM request latency distribution (histogram)
- llm_cost_usd: Total cost in USD (counter)
- llm_tokens_used: Total tokens processed (counter)
- llm_errors_total: Total number of errors (counter)
- monthly_budget_remaining_usd: Budget remaining for current month (gauge)
- monthly_spend_usd: Total spend for current month (gauge)

Usage:
    from src.core.metrics import (
        track_llm_request,
        track_llm_error,
        update_budget_metrics,
    )

    # Track successful request
    track_llm_request(
        provider="alibaba_cloud",
        model="qwen-plus",
        task_type="extraction",
        tokens_used=1200,
        cost_usd=0.0012,
        latency_seconds=0.45,
    )

    # Track error
    track_llm_error(provider="openai", task_type="generation", error_type="timeout")

    # Update budget metrics (call periodically)
    update_budget_metrics(cost_tracker)
"""


from prometheus_client import Counter, Gauge, Histogram

# LLM Request Counter
# Labels: provider (local_ollama, alibaba_cloud, openai)
#         task_type (extraction, generation, vision, embedding, etc.)
#         model (model name)
llm_requests_total = Counter(
    "llm_requests_total",
    "Total number of LLM requests",
    ["provider", "task_type", "model"],
)

# LLM Latency Histogram
# Buckets: 0.1s, 0.5s, 1s, 2s, 5s, 10s, 30s, 60s, +Inf
# Labels: provider, task_type
llm_latency_seconds = Histogram(
    "llm_latency_seconds",
    "LLM request latency in seconds",
    ["provider", "task_type"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, float("inf")),
)

# LLM Cost Counter (cumulative)
# Labels: provider
llm_cost_usd = Counter(
    "llm_cost_usd",
    "Total LLM cost in USD (cumulative)",
    ["provider"],
)

# LLM Tokens Counter
# Labels: provider, token_type (input, output, total)
llm_tokens_used = Counter(
    "llm_tokens_used",
    "Total tokens processed",
    ["provider", "token_type"],
)

# LLM Error Counter
# Labels: provider, task_type, error_type (timeout, rate_limit, api_error, etc.)
llm_errors_total = Counter(
    "llm_errors_total",
    "Total number of LLM errors",
    ["provider", "task_type", "error_type"],
)

# Monthly Budget Remaining (Gauge)
# Labels: provider
# Note: This is updated periodically, not on every request
monthly_budget_remaining_usd = Gauge(
    "monthly_budget_remaining_usd",
    "Monthly budget remaining in USD",
    ["provider"],
)

# Monthly Spend (Gauge)
# Labels: provider
# Note: This is updated periodically, not on every request
monthly_spend_usd = Gauge(
    "monthly_spend_usd",
    "Total spend for current month in USD",
    ["provider"],
)


def track_llm_request(
    provider: str,
    model: str,
    task_type: str,
    tokens_used: int,
    cost_usd: float,
    latency_seconds: float,
    tokens_input: int | None = None,
    tokens_output: int | None = None,
) -> None:
    """Track a successful LLM request.

    Args:
        provider: Provider name (local_ollama, alibaba_cloud, openai)
        model: Model name (e.g., qwen-plus, gpt-4o)
        task_type: Task type (extraction, generation, vision, embedding)
        tokens_used: Total tokens used (input + output)
        cost_usd: Cost in USD
        latency_seconds: Request latency in seconds
        tokens_input: Input tokens (optional)
        tokens_output: Output tokens (optional)

    Example:
        track_llm_request(
            provider="alibaba_cloud",
            model="qwen-plus",
            task_type="extraction",
            tokens_used=1200,
            cost_usd=0.0012,
            latency_seconds=0.45,
            tokens_input=800,
            tokens_output=400,
        )
    """
    # Increment request counter
    llm_requests_total.labels(provider=provider, task_type=task_type, model=model).inc()

    # Record latency
    llm_latency_seconds.labels(provider=provider, task_type=task_type).observe(latency_seconds)

    # Increment cost
    llm_cost_usd.labels(provider=provider).inc(cost_usd)

    # Increment tokens
    llm_tokens_used.labels(provider=provider, token_type="total").inc(tokens_used)

    # Track input/output tokens separately if available
    if tokens_input is not None:
        llm_tokens_used.labels(provider=provider, token_type="input").inc(tokens_input)
    if tokens_output is not None:
        llm_tokens_used.labels(provider=provider, token_type="output").inc(tokens_output)


def track_llm_error(
    provider: str,
    task_type: str,
    error_type: str,
) -> None:
    """Track an LLM error.

    Args:
        provider: Provider name (local_ollama, alibaba_cloud, openai)
        task_type: Task type (extraction, generation, vision, embedding)
        error_type: Error type (timeout, rate_limit, api_error, budget_exceeded, etc.)

    Example:
        track_llm_error(
            provider="openai",
            task_type="generation",
            error_type="timeout",
        )
    """
    llm_errors_total.labels(provider=provider, task_type=task_type, error_type=error_type).inc()


def update_budget_metrics(
    provider: str,
    monthly_spending: float,
    budget_limit: float,
) -> None:
    """Update budget-related gauge metrics.

    This should be called periodically (e.g., after each request or every minute)
    to update the current budget status in Prometheus.

    Args:
        provider: Provider name (alibaba_cloud, openai)
        monthly_spending: Current month spending in USD
        budget_limit: Monthly budget limit in USD (0.0 = unlimited)

    Example:
        # After tracking a request
        spending = cost_tracker.get_monthly_spending()
        for provider, spent in spending.items():
            limit = config.get_budget_limit(provider)
            update_budget_metrics(provider, spent, limit)
    """
    # Update monthly spend gauge
    monthly_spend_usd.labels(provider=provider).set(monthly_spending)

    # Update budget remaining gauge (only if limit is set)
    if budget_limit > 0.0:
        remaining = max(0.0, budget_limit - monthly_spending)
        monthly_budget_remaining_usd.labels(provider=provider).set(remaining)
    else:
        # Unlimited budget - set to -1.0 as sentinel
        monthly_budget_remaining_usd.labels(provider=provider).set(-1.0)
