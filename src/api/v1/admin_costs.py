"""Admin Cost API endpoints for LLM cost tracking and budget management.

Sprint 31 Feature 31.10a: Cost API Backend Implementation
Sprint 53 Feature 53.4: Extracted from admin.py

This module provides endpoints for:
- Cost statistics by provider and model
- Historical cost data for charting
- Budget status and utilization tracking
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Literal

import structlog
from fastapi import APIRouter, HTTPException, Query, status

from src.api.models.cost_stats import (
    BudgetStatus,
    CostHistory,
    CostStats,
    ModelCost,
    ProviderCost,
)
from src.components.llm_proxy.cost_tracker import get_cost_tracker
from src.core.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin-costs"])


@router.get("/costs/stats", response_model=CostStats)
async def get_cost_stats(
    time_range: Literal["7d", "30d", "all"] = Query(
        default="7d",
        description="Time range for cost statistics (7d=last 7 days, 30d=current month, all=all time)",
    )
) -> CostStats:
    """Get LLM cost statistics with budget tracking.

    **Sprint 31 Feature 31.10a: Cost Dashboard Backend**

    Returns comprehensive cost breakdown by provider, model, and budget status.
    Includes all LLM costs tracked by AegisLLMProxy via SQLite cost tracker.

    **Time Ranges:**
    - `7d`: Last 7 days (rolling window)
    - `30d`: Current month (from first day of month to now)
    - `all`: All time (entire cost tracking history)

    **Budget Status Thresholds:**
    - `ok`: <80% of budget used (green)
    - `warning`: 80-100% of budget used (yellow)
    - `critical`: >100% of budget used (red, over budget)

    **Provider Tracking:**
    - `local_ollama`: Always $0.00 (free local models)
    - `alibaba_cloud`: Qwen models (qwen3-vl, qwen-turbo, etc.)
    - `openai`: GPT models (if enabled)

    **Budget Configuration:**
    Budget limits are configured via environment variables:
    - `MONTHLY_BUDGET_ALIBABA_CLOUD`: Default $10.00/month
    - `MONTHLY_BUDGET_OPENAI`: Default $20.00/month

    Args:
        time_range: Time window for statistics (7d, 30d, all)

    Returns:
        CostStats: Comprehensive cost statistics

    Raises:
        HTTPException: If cost retrieval fails
    """
    try:
        tracker = get_cost_tracker()

        # Calculate time filter based on time_range
        start_date = None
        if time_range == "7d":
            start_date = (datetime.now() - timedelta(days=7)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif time_range == "30d":
            # Current month (from first day to now)
            start_date = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Get request stats from tracker
        with sqlite3.connect(tracker.db_path) as conn:
            cursor = conn.cursor()

            # Build WHERE clause
            conditions = []
            params = []
            if start_date:
                conditions.append("timestamp >= ?")
                params.append(start_date.isoformat())

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # Aggregate by provider
            cursor.execute(
                f"""
                SELECT
                    provider,
                    SUM(cost_usd) as total_cost,
                    SUM(tokens_total) as total_tokens,
                    COUNT(*) as total_calls
                FROM llm_requests
                WHERE {where_clause}
                GROUP BY provider
            """,
                tuple(params),
            )

            provider_rows = cursor.fetchall()

            # Aggregate by model
            cursor.execute(
                f"""
                SELECT
                    provider,
                    model,
                    SUM(cost_usd) as total_cost,
                    SUM(tokens_total) as total_tokens,
                    COUNT(*) as total_calls
                FROM llm_requests
                WHERE {where_clause}
                GROUP BY provider, model
            """,
                tuple(params),
            )

            model_rows = cursor.fetchall()

        # Build provider cost breakdown
        by_provider: dict[str, ProviderCost] = {}
        for provider, cost, tokens, calls in provider_rows:
            avg_cost = cost / calls if calls > 0 else 0.0
            by_provider[provider] = ProviderCost(
                cost_usd=cost,
                tokens=tokens,
                calls=calls,
                avg_cost_per_call=avg_cost,
            )

        # Build model cost breakdown
        by_model: dict[str, ModelCost] = {}
        for provider, model, cost, tokens, calls in model_rows:
            model_key = f"{provider}/{model}"
            by_model[model_key] = ModelCost(
                provider=provider,
                cost_usd=cost,
                tokens=tokens,
                calls=calls,
            )

        # Calculate totals
        total_cost = sum(p.cost_usd for p in by_provider.values())
        total_tokens = sum(p.tokens for p in by_provider.values())
        total_calls = sum(p.calls for p in by_provider.values())
        avg_cost_per_call = total_cost / total_calls if total_calls > 0 else 0.0

        # Calculate budget status (only for current month)
        budgets: dict[str, BudgetStatus] = {}

        # Get current month spending for budget calculation
        current_month_spending = tracker.get_monthly_spending()

        # Ollama (always free)
        if "local_ollama" in by_provider:
            budgets["local_ollama"] = BudgetStatus(
                limit_usd=0.0,
                spent_usd=0.0,
                utilization_percent=0.0,
                status="ok",
                remaining_usd=0.0,
            )

        # Alibaba Cloud
        if "alibaba_cloud" in current_month_spending or "alibaba_cloud" in by_provider:
            alibaba_limit = float(settings.monthly_budget_alibaba_cloud or 10.0)
            alibaba_spent = current_month_spending.get("alibaba_cloud", 0.0)
            alibaba_util = (alibaba_spent / alibaba_limit * 100) if alibaba_limit > 0 else 0.0

            budgets["alibaba_cloud"] = BudgetStatus(
                limit_usd=alibaba_limit,
                spent_usd=alibaba_spent,
                utilization_percent=alibaba_util,
                status=(
                    "ok" if alibaba_util < 80 else ("warning" if alibaba_util < 100 else "critical")
                ),
                remaining_usd=max(0, alibaba_limit - alibaba_spent),
            )

        # OpenAI
        if "openai" in current_month_spending or "openai" in by_provider:
            openai_limit = float(settings.monthly_budget_openai or 20.0)
            openai_spent = current_month_spending.get("openai", 0.0)
            openai_util = (openai_spent / openai_limit * 100) if openai_limit > 0 else 0.0

            budgets["openai"] = BudgetStatus(
                limit_usd=openai_limit,
                spent_usd=openai_spent,
                utilization_percent=openai_util,
                status=(
                    "ok" if openai_util < 80 else ("warning" if openai_util < 100 else "critical")
                ),
                remaining_usd=max(0, openai_limit - openai_spent),
            )

        logger.info(
            "cost_stats_retrieved",
            time_range=time_range,
            total_cost=total_cost,
            total_calls=total_calls,
            providers=list(by_provider.keys()),
        )

        return CostStats(
            total_cost_usd=total_cost,
            total_tokens=total_tokens,
            total_calls=total_calls,
            avg_cost_per_call=avg_cost_per_call,
            by_provider=by_provider,
            by_model=by_model,
            budgets=budgets,
            time_range=time_range,
        )

    except Exception as e:
        logger.error("cost_stats_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve cost statistics: {str(e)}",
        ) from e


@router.get("/costs/history", response_model=list[CostHistory])
async def get_cost_history(
    time_range: Literal["7d", "30d", "all"] = Query(
        default="7d",
        description="Time range for cost history (7d=last 7 days, 30d=last 30 days, all=all time)",
    )
) -> list[CostHistory]:
    """Get historical cost data grouped by day for charting.

    **Sprint 31 Feature 31.10a: Cost Dashboard Backend**

    Returns daily aggregated cost data for time-series visualization.
    Used by frontend to render cost trend charts and budget burn-down graphs.

    **Time Ranges:**
    - `7d`: Last 7 days (7 data points)
    - `30d`: Last 30 days (up to 30 data points)
    - `all`: All time (daily aggregation since first tracked request)

    **Data Aggregation:**
    - Costs are grouped by date (YYYY-MM-DD)
    - Tokens include both input and output
    - Calls are the number of LLM requests per day
    - Results are sorted chronologically (oldest to newest)

    Args:
        time_range: Time window for history (7d, 30d, all)

    Returns:
        List[CostHistory]: Daily cost data sorted by date

    Raises:
        HTTPException: If cost retrieval fails
    """
    try:
        tracker = get_cost_tracker()

        # Calculate time filter
        start_date = None
        if time_range == "7d":
            start_date = (datetime.now() - timedelta(days=7)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif time_range == "30d":
            start_date = (datetime.now() - timedelta(days=30)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

        # Query daily aggregates from database
        with sqlite3.connect(tracker.db_path) as conn:
            cursor = conn.cursor()

            # Build WHERE clause
            conditions = []
            params = []
            if start_date:
                conditions.append("timestamp >= ?")
                params.append(start_date.isoformat())

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            # Aggregate by date
            cursor.execute(
                f"""
                SELECT
                    date(timestamp) as date,
                    SUM(cost_usd) as total_cost,
                    SUM(tokens_total) as total_tokens,
                    COUNT(*) as total_calls
                FROM llm_requests
                WHERE {where_clause}
                GROUP BY date(timestamp)
                ORDER BY date ASC
            """,
                tuple(params),
            )

            rows = cursor.fetchall()

        # Build response
        history = [
            CostHistory(
                date=row[0],
                cost_usd=row[1],
                tokens=row[2],
                calls=row[3],
            )
            for row in rows
        ]

        logger.info(
            "cost_history_retrieved",
            time_range=time_range,
            data_points=len(history),
            start_date=start_date.isoformat() if start_date else "all_time",
        )

        return history

    except Exception as e:
        logger.error("cost_history_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve cost history: {str(e)}",
        ) from e


from pydantic import BaseModel


class TimeseriesDataPoint(BaseModel):
    """Individual data point for timeseries chart."""

    date: str
    tokens: int
    cost_usd: float
    provider: str


class TimeseriesResponse(BaseModel):
    """Response for timeseries endpoint."""

    data: list[TimeseriesDataPoint]
    total_tokens: int = 0
    total_cost_usd: float = 0.0


@router.get("/costs/timeseries", response_model=TimeseriesResponse)
async def get_cost_timeseries(
    start: str = Query(
        ...,
        description="Start date (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    end: str = Query(
        ...,
        description="End date (YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    aggregation: Literal["daily", "weekly", "monthly"] = Query(
        default="daily",
        description="Aggregation level (daily, weekly, monthly)",
    ),
    provider: str | None = Query(
        default=None,
        description="Filter by provider (e.g., ollama, alibaba_cloud)",
    ),
) -> TimeseriesResponse:
    """Get token usage timeseries data for charting.

    **Sprint 112 Feature 112.2: Cost Timeseries Endpoint**

    Returns token usage and cost data grouped by date for visualization
    in time-series charts. Supports filtering by provider and aggregation
    at different time granularities.

    **Aggregation Levels:**
    - `daily`: One data point per day (default)
    - `weekly`: One data point per week (ISO week)
    - `monthly`: One data point per month

    **Provider Filtering:**
    - `ollama`: Local Ollama models (free)
    - `alibaba_cloud`: Alibaba Cloud DashScope models
    - `openai`: OpenAI models (if configured)

    Args:
        start: Start date in YYYY-MM-DD format
        end: End date in YYYY-MM-DD format
        aggregation: Aggregation level (daily/weekly/monthly)
        provider: Optional provider filter

    Returns:
        TimeseriesResponse: Timeseries data with totals

    Raises:
        HTTPException: If data retrieval fails
    """
    try:
        tracker = get_cost_tracker()

        # Parse dates
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d")

        # Query database
        with sqlite3.connect(tracker.db_path) as conn:
            cursor = conn.cursor()

            # Build WHERE clause
            conditions = ["date(timestamp) >= ?", "date(timestamp) <= ?"]
            params: list = [start, end]

            if provider:
                conditions.append("provider = ?")
                params.append(provider)

            where_clause = " AND ".join(conditions)

            # Determine date grouping based on aggregation
            if aggregation == "weekly":
                date_group = "strftime('%Y-W%W', timestamp)"
            elif aggregation == "monthly":
                date_group = "strftime('%Y-%m', timestamp)"
            else:
                date_group = "date(timestamp)"

            # Query with aggregation by provider
            cursor.execute(
                f"""
                SELECT
                    {date_group} as period,
                    provider,
                    SUM(tokens_total) as total_tokens,
                    SUM(cost_usd) as total_cost
                FROM llm_requests
                WHERE {where_clause}
                GROUP BY {date_group}, provider
                ORDER BY period ASC, provider ASC
            """,
                tuple(params),
            )

            rows = cursor.fetchall()

        # Build response data
        data_points: list[TimeseriesDataPoint] = []
        total_tokens = 0
        total_cost_usd = 0.0

        for period, prov, tokens, cost in rows:
            data_points.append(
                TimeseriesDataPoint(
                    date=period,
                    tokens=tokens or 0,
                    cost_usd=cost or 0.0,
                    provider=prov or "unknown",
                )
            )
            total_tokens += tokens or 0
            total_cost_usd += cost or 0.0

        logger.info(
            "cost_timeseries_retrieved",
            start=start,
            end=end,
            aggregation=aggregation,
            provider=provider,
            data_points=len(data_points),
            total_tokens=total_tokens,
        )

        return TimeseriesResponse(
            data=data_points,
            total_tokens=total_tokens,
            total_cost_usd=round(total_cost_usd, 4),
        )

    except Exception as e:
        logger.error("cost_timeseries_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve timeseries data: {str(e)}",
        ) from e
