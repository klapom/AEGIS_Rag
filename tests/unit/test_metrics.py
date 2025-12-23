"""Unit tests for Prometheus metrics.

Sprint 24 - Feature 24.1: Prometheus Metrics Implementation
Related ADR: ADR-033

Tests cover:
- Metric object existence
- Counter increments
- Histogram observations
- Gauge updates
- Budget calculations
- Error tracking
"""

import pytest

from src.core.metrics import (
    llm_cost_usd,
    llm_errors_total,
    llm_latency_seconds,
    llm_requests_total,
    llm_tokens_used,
    monthly_budget_remaining_usd,
    monthly_spend_usd,
    track_llm_error,
    track_llm_request,
    update_budget_metrics,
)


class TestMetricRegistration:
    """Test that all metrics are properly defined."""

    def test_metrics_exist(self):
        """Verify all LLM metrics are defined and accessible."""
        # Simply verify the metric objects exist and are the right type
        assert llm_requests_total is not None
        assert llm_latency_seconds is not None
        assert llm_cost_usd is not None
        assert llm_tokens_used is not None
        assert llm_errors_total is not None
        assert monthly_budget_remaining_usd is not None
        assert monthly_spend_usd is not None

    def test_metrics_have_correct_names(self):
        """Verify metrics have correct Prometheus names."""
        # Note: Counter metrics internally store name without _total suffix
        # The _total suffix is added by Prometheus when exposing metrics
        assert llm_requests_total._name == "llm_requests"
        assert llm_latency_seconds._name == "llm_latency_seconds"
        assert llm_cost_usd._name == "llm_cost_usd"
        assert llm_tokens_used._name == "llm_tokens_used"
        assert llm_errors_total._name == "llm_errors"


class TestTrackLLMRequest:
    """Test track_llm_request function."""

    def test_track_request_increments_counter(self):
        """Verify request counter increments."""
        # Get initial value
        initial = llm_requests_total.labels(
            provider="test_local", task_type="test_extraction", model="test_gemma"
        )._value.get()

        # Track request
        track_llm_request(
            provider="test_local",
            model="test_gemma",
            task_type="test_extraction",
            tokens_used=500,
            cost_usd=0.0,
            latency_seconds=0.3,
        )

        # Verify increment
        new_value = llm_requests_total.labels(
            provider="test_local", task_type="test_extraction", model="test_gemma"
        )._value.get()
        assert new_value == initial + 1

    def test_track_request_records_latency(self):
        """Verify latency histogram records observations."""
        # Get initial sum (Histograms track sum of all observed values)
        initial_sum = llm_latency_seconds.labels(
            provider="test_alibaba", task_type="test_generation"
        )._sum.get()

        # Track request with latency
        track_llm_request(
            provider="test_alibaba",
            model="qwen-plus",
            task_type="test_generation",
            tokens_used=1000,
            cost_usd=0.001,
            latency_seconds=1.5,
        )

        # Verify histogram sum increased by the observed latency
        new_sum = llm_latency_seconds.labels(
            provider="test_alibaba", task_type="test_generation"
        )._sum.get()
        assert new_sum >= initial_sum + 1.5

    def test_track_request_increments_cost(self):
        """Verify cost counter increments."""
        # Get initial cost
        initial = llm_cost_usd.labels(provider="test_openai")._value.get()

        # Track request with cost
        track_llm_request(
            provider="test_openai",
            model="gpt-4o",
            task_type="generation",
            tokens_used=2000,
            cost_usd=0.125,
            latency_seconds=2.0,
        )

        # Verify increment
        new_cost = llm_cost_usd.labels(provider="test_openai")._value.get()
        assert new_cost >= initial + 0.125

    def test_track_request_increments_tokens(self):
        """Verify token counter increments."""
        # Get initial tokens
        initial = llm_tokens_used.labels(provider="test_local2", token_type="total")._value.get()

        # Track request with tokens
        track_llm_request(
            provider="test_local2",
            model="llama3.2",
            task_type="embedding",
            tokens_used=1500,
            cost_usd=0.0,
            latency_seconds=0.1,
        )

        # Verify increment
        new_tokens = llm_tokens_used.labels(provider="test_local2", token_type="total")._value.get()
        assert new_tokens >= initial + 1500

    def test_track_request_with_input_output_tokens(self):
        """Verify input/output token tracking."""
        # Get initial values
        initial_input = llm_tokens_used.labels(
            provider="test_alibaba2", token_type="input"
        )._value.get()
        initial_output = llm_tokens_used.labels(
            provider="test_alibaba2", token_type="output"
        )._value.get()

        # Track request with split tokens
        track_llm_request(
            provider="test_alibaba2",
            model="qwen-turbo",
            task_type="extraction",
            tokens_used=1200,
            cost_usd=0.0006,
            latency_seconds=0.8,
            tokens_input=800,
            tokens_output=400,
        )

        # Verify increments
        new_input = llm_tokens_used.labels(
            provider="test_alibaba2", token_type="input"
        )._value.get()
        new_output = llm_tokens_used.labels(
            provider="test_alibaba2", token_type="output"
        )._value.get()

        assert new_input >= initial_input + 800
        assert new_output >= initial_output + 400


class TestTrackLLMError:
    """Test track_llm_error function."""

    def test_track_error_increments_counter(self):
        """Verify error counter increments."""
        # Get initial value
        initial = llm_errors_total.labels(
            provider="test_openai2", task_type="generation", error_type="timeout"
        )._value.get()

        # Track error
        track_llm_error(provider="test_openai2", task_type="generation", error_type="timeout")

        # Verify increment
        new_errors = llm_errors_total.labels(
            provider="test_openai2", task_type="generation", error_type="timeout"
        )._value.get()
        assert new_errors == initial + 1

    def test_track_different_error_types(self):
        """Verify different error types are tracked separately."""
        # Track different errors
        track_llm_error(provider="test_alibaba3", task_type="extraction", error_type="rate_limit")
        track_llm_error(provider="test_alibaba3", task_type="extraction", error_type="api_error")
        track_llm_error(
            provider="test_alibaba3", task_type="extraction", error_type="budget_exceeded"
        )

        # Verify each type has at least 1 count
        rate_limit = llm_errors_total.labels(
            provider="test_alibaba3", task_type="extraction", error_type="rate_limit"
        )._value.get()
        api_error = llm_errors_total.labels(
            provider="test_alibaba3", task_type="extraction", error_type="api_error"
        )._value.get()
        budget = llm_errors_total.labels(
            provider="test_alibaba3", task_type="extraction", error_type="budget_exceeded"
        )._value.get()

        assert rate_limit > 0
        assert api_error > 0
        assert budget > 0


class TestUpdateBudgetMetrics:
    """Test update_budget_metrics function."""

    def test_update_spend_gauge(self):
        """Verify monthly spend gauge updates."""
        # Update budget metrics
        update_budget_metrics(provider="test_alibaba4", monthly_spending=5.25, budget_limit=10.0)

        # Verify gauge value
        spend = monthly_spend_usd.labels(provider="test_alibaba4")._value.get()
        assert spend == 5.25

    def test_update_budget_remaining_with_limit(self):
        """Verify budget remaining calculation with limit."""
        # Update with budget limit
        update_budget_metrics(provider="test_openai3", monthly_spending=12.50, budget_limit=20.0)

        # Verify remaining
        remaining = monthly_budget_remaining_usd.labels(provider="test_openai3")._value.get()
        assert remaining == 7.50  # 20.0 - 12.50

    def test_update_budget_remaining_unlimited(self):
        """Verify budget remaining with unlimited budget (0.0)."""
        # Update with no limit
        update_budget_metrics(provider="test_local3", monthly_spending=0.0, budget_limit=0.0)

        # Verify unlimited sentinel
        remaining = monthly_budget_remaining_usd.labels(provider="test_local3")._value.get()
        assert remaining == -1.0  # Sentinel for unlimited

    def test_update_budget_exceeded(self):
        """Verify budget remaining when exceeded."""
        # Update with exceeded budget
        update_budget_metrics(provider="test_alibaba5", monthly_spending=15.0, budget_limit=10.0)

        # Verify remaining (should be 0.0, not negative)
        remaining = monthly_budget_remaining_usd.labels(provider="test_alibaba5")._value.get()
        assert remaining == 0.0


class TestMetricsIntegration:
    """Integration tests for metrics tracking."""

    def test_full_request_lifecycle(self):
        """Test complete request tracking with all metrics."""
        provider = "test_alibaba6"
        model = "qwen-plus"
        task_type = "extraction"

        # Get initial values
        initial_requests = llm_requests_total.labels(
            provider=provider, task_type=task_type, model=model
        )._value.get()
        initial_cost = llm_cost_usd.labels(provider=provider)._value.get()

        # Track request
        track_llm_request(
            provider=provider,
            model=model,
            task_type=task_type,
            tokens_used=2000,
            cost_usd=0.002,
            latency_seconds=1.2,
            tokens_input=1200,
            tokens_output=800,
        )

        # Update budget
        update_budget_metrics(provider=provider, monthly_spending=0.002, budget_limit=10.0)

        # Verify all metrics updated
        new_requests = llm_requests_total.labels(
            provider=provider, task_type=task_type, model=model
        )._value.get()
        new_cost = llm_cost_usd.labels(provider=provider)._value.get()
        spend = monthly_spend_usd.labels(provider=provider)._value.get()
        remaining = monthly_budget_remaining_usd.labels(provider=provider)._value.get()

        assert new_requests == initial_requests + 1
        assert new_cost >= initial_cost + 0.002
        assert spend == 0.002
        assert remaining == pytest.approx(9.998, rel=1e-3)

    def test_multiple_providers_tracked_separately(self):
        """Test that different providers track metrics independently."""
        # Track requests for different providers
        track_llm_request(
            provider="test_local4",
            model="llama3.2",
            task_type="generation",
            tokens_used=1000,
            cost_usd=0.0,
            latency_seconds=0.5,
        )

        track_llm_request(
            provider="test_alibaba7",
            model="qwen-turbo",
            task_type="generation",
            tokens_used=1000,
            cost_usd=0.001,
            latency_seconds=0.8,
        )

        # Verify separate tracking - local should be 0, cloud should have cost
        local_cost = llm_cost_usd.labels(provider="test_local4")._value.get()
        cloud_cost = llm_cost_usd.labels(provider="test_alibaba7")._value.get()

        assert local_cost == 0.0  # Local is free
        assert cloud_cost > 0.0  # Cloud has cost
