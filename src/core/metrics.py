"""Prometheus Metrics for AegisRAG System Monitoring.

Sprint 24 - Feature 24.1: Prometheus Metrics Implementation (LLM metrics)
Sprint 25 - Feature 25.1: Extended Metrics (System metrics)
Related ADR: ADR-033 (Multi-Cloud LLM Execution)

This module provides Prometheus metrics for monitoring LLM usage, cost tracking,
performance, and system health across multiple providers (Local Ollama, Alibaba Cloud, OpenAI).

Metrics Exported:
- llm_requests_total: Total number of LLM requests (counter)
- llm_latency_seconds: LLM request latency distribution (histogram)
- llm_cost_usd: Total cost in USD (counter)
- llm_tokens_used: Total tokens processed (counter)
- llm_errors_total: Total number of errors (counter)
- monthly_budget_remaining_usd: Budget remaining for current month (gauge)
- monthly_spend_usd: Total spend for current month (gauge)
- qdrant_points_count: Number of points in Qdrant collections (gauge)
- neo4j_entities_count: Number of entities in Neo4j (gauge)
- neo4j_relations_count: Number of relationships in Neo4j (gauge)

Usage:
    from src.core.metrics import (
        track_llm_request,
        track_llm_error,
        update_budget_metrics,
        update_qdrant_metrics,
        update_neo4j_metrics,
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
    update_budget_metrics("alibaba_cloud", 5.25, 10.0)

    # Update system metrics (call periodically)
    update_qdrant_metrics("documents", 15420)
    update_neo4j_metrics(542, 1834)
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


# ============================================================================
# SYSTEM METRICS (Sprint 25 - Feature 25.1)
# ============================================================================

# Qdrant vector database points count
qdrant_points_count = Gauge(
    "qdrant_points_count",
    "Number of points in Qdrant collection",
    ["collection"],
)

# Neo4j entity count
neo4j_entities_count = Gauge(
    "neo4j_entities_count",
    "Number of entities in Neo4j knowledge graph",
)

# Neo4j relationship count
neo4j_relations_count = Gauge(
    "neo4j_relations_count",
    "Number of relationships in Neo4j knowledge graph",
)


def update_qdrant_metrics(collection: str, points_count: int) -> None:
    """Update Qdrant collection metrics.

    Args:
        collection: Collection name
        points_count: Number of points in collection

    Example:
        update_qdrant_metrics("documents", 15420)
    """
    qdrant_points_count.labels(collection=collection).set(points_count)


def update_neo4j_metrics(entities_count: int, relations_count: int) -> None:
    """Update Neo4j knowledge graph metrics.

    Args:
        entities_count: Number of entities in graph
        relations_count: Number of relationships in graph

    Example:
        update_neo4j_metrics(entities_count=542, relations_count=1834)
    """
    neo4j_entities_count.set(entities_count)
    neo4j_relations_count.set(relations_count)


# ============================================================================
# SPRINT 69 - FEATURE 69.7: PRODUCTION MONITORING & OBSERVABILITY
# ============================================================================

# Query metrics
query_total = Counter(
    "aegis_queries_total",
    "Total number of queries processed",
    ["intent", "model"],
)

query_latency_seconds = Histogram(
    "aegis_query_latency_seconds",
    "Query processing latency in seconds",
    ["stage"],  # stage: intent_classification, retrieval, generation, total
    buckets=(0.1, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0, float("inf")),
)

# Cache metrics
cache_hits_total = Counter(
    "aegis_cache_hits_total",
    "Total cache hits",
    ["cache_type"],  # cache_type: redis, embedding, llm_config
)

cache_misses_total = Counter(
    "aegis_cache_misses_total",
    "Total cache misses",
    ["cache_type"],
)

# Memory metrics (Graphiti temporal memory)
memory_facts_count = Gauge(
    "aegis_memory_facts_count",
    "Number of facts in temporal memory",
    ["fact_type"],  # fact_type: episodic, semantic, entity
)

# Error metrics
error_total = Counter(
    "aegis_errors_total",
    "Total errors by type",
    ["error_type"],  # error_type: llm_error, database_error, timeout, validation_error
)


def track_query(
    intent: str,
    model: str,
    stage_latencies: dict[str, float],
) -> None:
    """Track a complete query with latencies by stage.

    Args:
        intent: Query intent (vector_search, graph_reasoning, hybrid, memory_retrieval)
        model: LLM model used for generation
        stage_latencies: Dict mapping stage name to latency in seconds
            Example: {
                "intent_classification": 0.05,
                "retrieval": 0.3,
                "generation": 0.8,
                "total": 1.15
            }

    Example:
        track_query(
            intent="hybrid",
            model="nemotron-no-think:latest",
            stage_latencies={
                "intent_classification": 0.05,
                "retrieval": 0.3,
                "generation": 0.8,
                "total": 1.15
            }
        )
    """
    # Increment query counter
    query_total.labels(intent=intent, model=model).inc()

    # Record latencies for each stage
    for stage, latency in stage_latencies.items():
        query_latency_seconds.labels(stage=stage).observe(latency)


def track_cache_hit(cache_type: str) -> None:
    """Track a cache hit.

    Args:
        cache_type: Type of cache (redis, embedding, llm_config)

    Example:
        track_cache_hit("redis")
    """
    cache_hits_total.labels(cache_type=cache_type).inc()


def track_cache_miss(cache_type: str) -> None:
    """Track a cache miss.

    Args:
        cache_type: Type of cache (redis, embedding, llm_config)

    Example:
        track_cache_miss("embedding")
    """
    cache_misses_total.labels(cache_type=cache_type).inc()


def update_memory_facts(fact_type: str, count: int) -> None:
    """Update memory facts count.

    Args:
        fact_type: Type of fact (episodic, semantic, entity)
        count: Number of facts

    Example:
        update_memory_facts("episodic", 1234)
    """
    memory_facts_count.labels(fact_type=fact_type).set(count)


def track_error(error_type: str) -> None:
    """Track an error occurrence.

    Args:
        error_type: Type of error (llm_error, database_error, timeout, validation_error)

    Example:
        track_error("timeout")
    """
    error_total.labels(error_type=error_type).inc()


# ============================================================================
# SPRINT 70 - FEATURE 70.10: TOOL USE ANALYTICS & MONITORING
# ============================================================================

# Tool execution counter
# Labels: tool_name (name of MCP tool), status (success, failed)
tool_executions_total = Counter(
    "aegis_tool_executions_total",
    "Total number of tool executions",
    ["tool_name", "status"],
)

# Tool execution latency histogram
# Labels: tool_name
# Buckets: 0.1s, 0.5s, 1s, 2s, 5s, 10s, 30s, 60s, +Inf
tool_execution_duration_seconds = Histogram(
    "aegis_tool_execution_duration_seconds",
    "Tool execution latency in seconds",
    ["tool_name"],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, float("inf")),
)

# Active tool executions gauge
# No labels - tracks concurrent tool executions
active_tool_executions = Gauge(
    "aegis_active_tool_executions",
    "Number of currently executing tools",
)


def track_tool_execution(
    tool_name: str,
    status: str,
    duration_seconds: float,
) -> None:
    """Track a tool execution with metrics.

    **Sprint 70 Feature 70.10: Tool Analytics**

    Records tool execution count, status (success/failed), and latency.

    Args:
        tool_name: Name of the MCP tool executed
        status: Execution status ("success" or "failed")
        duration_seconds: Tool execution time in seconds

    Example:
        >>> track_tool_execution(
        ...     tool_name="web_search",
        ...     status="success",
        ...     duration_seconds=0.45
        ... )
        >>> track_tool_execution(
        ...     tool_name="file_read",
        ...     status="failed",
        ...     duration_seconds=0.12
        ... )
    """
    # Increment execution counter
    tool_executions_total.labels(tool_name=tool_name, status=status).inc()

    # Record latency
    tool_execution_duration_seconds.labels(tool_name=tool_name).observe(duration_seconds)


def increment_active_tools() -> None:
    """Increment active tool executions counter.

    **Sprint 70 Feature 70.10: Tool Analytics**

    Call this when a tool execution starts.

    Example:
        >>> increment_active_tools()
    """
    active_tool_executions.inc()


def decrement_active_tools() -> None:
    """Decrement active tool executions counter.

    **Sprint 70 Feature 70.10: Tool Analytics**

    Call this when a tool execution completes (success or failure).

    Example:
        >>> decrement_active_tools()
    """
    active_tool_executions.dec()
