"""Pydantic models for LLM cost statistics API.

Sprint 31 Feature 31.10a: Cost API Backend Implementation

This module defines request/response models for the admin cost dashboard,
providing structured data for LLM cost tracking, budget monitoring, and
historical cost analysis.

Models:
    - ProviderCost: Cost breakdown per provider (local_ollama, alibaba_cloud, openai)
    - ModelCost: Cost breakdown per model
    - BudgetStatus: Budget utilization tracking (ok/warning/critical)
    - CostStats: Complete cost statistics (primary response model)
    - CostHistory: Daily cost data for charting

Example:
    >>> from src.api.models.cost_stats import CostStats, BudgetStatus
    >>> stats = CostStats(
    ...     total_cost_usd=15.25,
    ...     total_tokens=1_000_000,
    ...     total_calls=500,
    ...     avg_cost_per_call=0.0305,
    ...     by_provider={
    ...         "alibaba_cloud": ProviderCost(
    ...             cost_usd=15.25,
    ...             tokens=1_000_000,
    ...             calls=500,
    ...             avg_cost_per_call=0.0305
    ...         )
    ...     },
    ...     by_model={},
    ...     budgets={
    ...         "alibaba_cloud": BudgetStatus(
    ...             limit_usd=10.0,
    ...             spent_usd=15.25,
    ...             utilization_percent=152.5,
    ...             status="critical",
    ...             remaining_usd=0.0
    ...         )
    ...     },
    ...     time_range="7d"
    ... )
    >>> stats.budgets["alibaba_cloud"].status
    'critical'

See Also:
    - src/components/llm_proxy/cost_tracker.py: SQLite cost tracker implementation
    - src/api/v1/admin.py: Admin endpoints using these models
"""

from typing import Literal

from pydantic import BaseModel, Field


class ProviderCost(BaseModel):
    """Cost breakdown for a specific provider.

    Aggregates all costs for a given provider (local_ollama, alibaba_cloud, openai)
    across all models and task types within the selected time range.

    Attributes:
        cost_usd: Total cost in USD
        tokens: Total tokens processed (input + output)
        calls: Number of API calls (requests)
        avg_cost_per_call: Average cost per call (cost_usd / calls)

    Example:
        >>> provider_cost = ProviderCost(
        ...     cost_usd=5.25,
        ...     tokens=100_000,
        ...     calls=50,
        ...     avg_cost_per_call=0.105
        ... )
        >>> provider_cost.cost_usd
        5.25
    """

    cost_usd: float = Field(..., description="Total cost in USD")
    tokens: int = Field(..., description="Total tokens processed (input + output)")
    calls: int = Field(..., description="Number of API calls")
    avg_cost_per_call: float = Field(..., description="Average cost per call")


class ModelCost(BaseModel):
    """Cost breakdown for a specific model.

    Tracks costs for a single model within a provider (e.g., qwen3-vl-30b on alibaba_cloud).

    Attributes:
        provider: Provider name (local_ollama, alibaba_cloud, openai)
        cost_usd: Total cost in USD for this model
        tokens: Total tokens processed (input + output)
        calls: Number of API calls for this model

    Example:
        >>> model_cost = ModelCost(
        ...     provider="alibaba_cloud",
        ...     cost_usd=3.50,
        ...     tokens=50_000,
        ...     calls=25
        ... )
        >>> model_cost.provider
        'alibaba_cloud'
    """

    provider: str = Field(..., description="Provider name")
    cost_usd: float = Field(..., description="Total cost in USD")
    tokens: int = Field(..., description="Total tokens processed (input + output)")
    calls: int = Field(..., description="Number of API calls")


class BudgetStatus(BaseModel):
    """Budget utilization for a provider.

    Tracks monthly budget limits and spending with threshold-based alerts.

    Status Thresholds:
        - ok: <80% of budget used (green)
        - warning: 80-100% of budget used (yellow)
        - critical: >100% of budget used (red, over budget)

    Attributes:
        limit_usd: Monthly budget limit in USD (from config)
        spent_usd: Current month spending in USD
        utilization_percent: Percentage of budget used
        status: Budget health status (ok/warning/critical)
        remaining_usd: Remaining budget (max(0, limit - spent))

    Example:
        >>> budget = BudgetStatus(
        ...     limit_usd=10.0,
        ...     spent_usd=8.5,
        ...     utilization_percent=85.0,
        ...     status="warning",
        ...     remaining_usd=1.5
        ... )
        >>> budget.status
        'warning'
        >>> budget.utilization_percent > 80
        True
    """

    limit_usd: float = Field(..., description="Monthly budget limit in USD")
    spent_usd: float = Field(..., description="Current month spending in USD")
    utilization_percent: float = Field(..., description="Percentage of budget used")
    status: Literal["ok", "warning", "critical"] = Field(
        ..., description="ok: <80%, warning: 80-100%, critical: >100%"
    )
    remaining_usd: float = Field(..., description="Remaining budget (max(0, limit - spent))")


class CostStats(BaseModel):
    """Complete cost statistics.

    Primary response model for GET /api/v1/admin/costs/stats endpoint.
    Provides comprehensive cost breakdown by provider, model, and budget status.

    Attributes:
        total_cost_usd: Total cost across all providers
        total_tokens: Total tokens processed (input + output)
        total_calls: Total API calls
        avg_cost_per_call: Average cost per call (total_cost / total_calls)
        by_provider: Cost breakdown by provider (dict: provider_name -> ProviderCost)
        by_model: Cost breakdown by model (dict: "provider/model" -> ModelCost)
        budgets: Budget status per provider (dict: provider_name -> BudgetStatus)
        time_range: Time range filter applied (7d, 30d, all)

    Example:
        >>> stats = CostStats(
        ...     total_cost_usd=15.25,
        ...     total_tokens=1_000_000,
        ...     total_calls=500,
        ...     avg_cost_per_call=0.0305,
        ...     by_provider={
        ...         "alibaba_cloud": ProviderCost(cost_usd=15.25, tokens=1_000_000, calls=500, avg_cost_per_call=0.0305)
        ...     },
        ...     by_model={
        ...         "alibaba_cloud/qwen3-vl-30b": ModelCost(provider="alibaba_cloud", cost_usd=15.25, tokens=1_000_000, calls=500)
        ...     },
        ...     budgets={
        ...         "alibaba_cloud": BudgetStatus(limit_usd=10.0, spent_usd=15.25, utilization_percent=152.5, status="critical", remaining_usd=0.0)
        ...     },
        ...     time_range="7d"
        ... )
        >>> stats.total_cost_usd
        15.25
        >>> stats.budgets["alibaba_cloud"].status
        'critical'
    """

    total_cost_usd: float = Field(..., description="Total cost across all providers")
    total_tokens: int = Field(..., description="Total tokens processed (input + output)")
    total_calls: int = Field(..., description="Total API calls")
    avg_cost_per_call: float = Field(..., description="Average cost per call")
    by_provider: dict[str, ProviderCost] = Field(..., description="Cost by provider")
    by_model: dict[str, ModelCost] = Field(..., description="Cost by model (provider/model)")
    budgets: dict[str, BudgetStatus] = Field(..., description="Budget status per provider")
    time_range: str = Field(..., description="Time range filter applied (7d, 30d, all)")


class CostHistory(BaseModel):
    """Historical cost data for charting.

    Daily cost aggregation for time-series visualization on the frontend.
    Used by GET /api/v1/admin/costs/history endpoint.

    Attributes:
        date: Date in YYYY-MM-DD format
        cost_usd: Total cost for this date
        tokens: Total tokens for this date
        calls: Total calls for this date

    Example:
        >>> history = CostHistory(
        ...     date="2025-11-20",
        ...     cost_usd=2.35,
        ...     tokens=50_000,
        ...     calls=25
        ... )
        >>> history.date
        '2025-11-20'
    """

    date: str = Field(..., description="Date in YYYY-MM-DD format")
    cost_usd: float = Field(..., description="Cost for this date")
    tokens: int = Field(..., description="Tokens for this date")
    calls: int = Field(..., description="Calls for this date")
