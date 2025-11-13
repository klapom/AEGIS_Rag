"""Unit tests for Prometheus metrics.

Sprint 24 - Feature 24.1: Prometheus Metrics Implementation
Related ADR: ADR-033

Tests cover:
- Metric registration and labeling
- Counter increments
- Histogram observations
- Gauge updates
- Budget calculations
- Error tracking
"""

import pytest
from prometheus_client import REGISTRY

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
    """Test that all metrics are properly registered with Prometheus."""

    def test_metrics_registered(self):
        """Verify all LLM metrics are registered in Prometheus registry."""
        registered_names = []
        for family in REGISTRY.collect():
            # Get the metric name without suffix (_total, _count, _bucket, etc.)
            # Prometheus adds these suffixes automatically
            base_name = family.name
            registered_names.append(base_name)

        # Note: Prometheus Counter automatically appends _total suffix
        # So llm_requests_total is registered as "llm_requests"
        assert "llm_requests" in registered_names or "llm_requests_total" in registered_names
        assert "llm_latency_seconds" in registered_names
        assert "llm_cost_usd" in registered_names
        assert "llm_tokens_used" in registered_names
        assert "llm_errors" in registered_names or "llm_errors_total" in registered_names
        assert "monthly_budget_remaining_usd" in registered_names
        assert "monthly_spend_usd" in registered_names

    def test_request_counter_labels(self):
        """Verify llm_requests_total has correct labels."""
        # Track a request to create label
        track_llm_request(
            provider="test_provider",
            model="test_model",
            task_type="test_task",
            tokens_used=100,
            cost_usd=0.01,
            latency_seconds=0.5,
        )

        # Get metric (Prometheus drops _total from Counter names)
        for family in REGISTRY.collect():
            if family.name in ["llm_requests_total", "llm_requests"]:
                for sample in family.samples:
                    if "test_provider" in str(sample.labels):
                        assert "provider" in sample.labels
                        assert "task_type" in sample.labels
                        assert "model" in sample.labels
                        return

        pytest.fail("llm_requests metric not found with correct labels")


class TestTrackLLMRequest:
    """Test track_llm_request function."""

    def test_track_request_increments_counter(self):
        """Verify request counter increments."""
        # Get initial value (try both names)
        initial_value = self._get_counter_value(
            "llm_requests", provider="local_ollama", task_type="extraction", model="gemma"
        )
        if initial_value == 0.0:
            initial_value = self._get_counter_value(
                "llm_requests_total", provider="local_ollama", task_type="extraction", model="gemma"
            )

        # Track request
        track_llm_request(
            provider="local_ollama",
            model="gemma",
            task_type="extraction",
            tokens_used=500,
            cost_usd=0.0,
            latency_seconds=0.3,
        )

        # Verify increment (try both names)
        new_value = self._get_counter_value(
            "llm_requests", provider="local_ollama", task_type="extraction", model="gemma"
        )
        if new_value == 0.0:
            new_value = self._get_counter_value(
                "llm_requests_total", provider="local_ollama", task_type="extraction", model="gemma"
            )
        assert new_value == initial_value + 1

    def test_track_request_records_latency(self):
        """Verify latency histogram records observations."""
        # Track request with latency
        track_llm_request(
            provider="alibaba_cloud",
            model="qwen-plus",
            task_type="generation",
            tokens_used=1000,
            cost_usd=0.001,
            latency_seconds=1.5,
        )

        # Verify histogram has observation
        for family in REGISTRY.collect():
            if family.name == "llm_latency_seconds":
                for sample in family.samples:
                    if (
                        sample.labels.get("provider") == "alibaba_cloud"
                        and sample.labels.get("task_type") == "generation"
                    ):
                        if sample.name.endswith("_count"):
                            assert sample.value > 0
                            return

        pytest.fail("Latency histogram observation not found")

    def test_track_request_increments_cost(self):
        """Verify cost counter increments."""
        initial_cost = self._get_counter_value("llm_cost_usd", provider="openai")

        # Track request with cost
        track_llm_request(
            provider="openai",
            model="gpt-4o",
            task_type="generation",
            tokens_used=2000,
            cost_usd=0.125,
            latency_seconds=2.0,
        )

        new_cost = self._get_counter_value("llm_cost_usd", provider="openai")
        assert new_cost >= initial_cost + 0.125

    def test_track_request_increments_tokens(self):
        """Verify token counter increments."""
        initial_tokens = self._get_counter_value(
            "llm_tokens_used", provider="local_ollama", token_type="total"
        )

        # Track request with tokens
        track_llm_request(
            provider="local_ollama",
            model="llama3.2",
            task_type="embedding",
            tokens_used=1500,
            cost_usd=0.0,
            latency_seconds=0.1,
        )

        new_tokens = self._get_counter_value(
            "llm_tokens_used", provider="local_ollama", token_type="total"
        )
        assert new_tokens >= initial_tokens + 1500

    def test_track_request_with_input_output_tokens(self):
        """Verify input/output token tracking."""
        initial_input = self._get_counter_value(
            "llm_tokens_used", provider="alibaba_cloud", token_type="input"
        )
        initial_output = self._get_counter_value(
            "llm_tokens_used", provider="alibaba_cloud", token_type="output"
        )

        # Track request with split tokens
        track_llm_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="extraction",
            tokens_used=1200,
            cost_usd=0.0006,
            latency_seconds=0.8,
            tokens_input=800,
            tokens_output=400,
        )

        new_input = self._get_counter_value(
            "llm_tokens_used", provider="alibaba_cloud", token_type="input"
        )
        new_output = self._get_counter_value(
            "llm_tokens_used", provider="alibaba_cloud", token_type="output"
        )

        assert new_input >= initial_input + 800
        assert new_output >= initial_output + 400

    def _get_counter_value(self, metric_name, **labels):
        """Helper to get counter value by labels."""
        for family in REGISTRY.collect():
            if family.name == metric_name:
                for sample in family.samples:
                    if all(sample.labels.get(k) == v for k, v in labels.items()):
                        return sample.value
        return 0.0


class TestTrackLLMError:
    """Test track_llm_error function."""

    def test_track_error_increments_counter(self):
        """Verify error counter increments."""
        # Try both metric names
        initial_errors = self._get_counter_value(
            "llm_errors",
            provider="openai",
            task_type="generation",
            error_type="timeout",
        )
        if initial_errors == 0.0:
            initial_errors = self._get_counter_value(
                "llm_errors_total",
                provider="openai",
                task_type="generation",
                error_type="timeout",
            )

        # Track error
        track_llm_error(provider="openai", task_type="generation", error_type="timeout")

        # Try both metric names
        new_errors = self._get_counter_value(
            "llm_errors",
            provider="openai",
            task_type="generation",
            error_type="timeout",
        )
        if new_errors == 0.0:
            new_errors = self._get_counter_value(
                "llm_errors_total",
                provider="openai",
                task_type="generation",
                error_type="timeout",
            )

        assert new_errors == initial_errors + 1

    def test_track_different_error_types(self):
        """Verify different error types are tracked separately."""
        # Track different errors
        track_llm_error(provider="alibaba_cloud", task_type="extraction", error_type="rate_limit")
        track_llm_error(provider="alibaba_cloud", task_type="extraction", error_type="api_error")
        track_llm_error(
            provider="alibaba_cloud", task_type="extraction", error_type="budget_exceeded"
        )

        # Verify each type (try both metric names)
        def get_error_count(error_type):
            count = self._get_counter_value(
                "llm_errors",
                provider="alibaba_cloud",
                task_type="extraction",
                error_type=error_type,
            )
            if count == 0.0:
                count = self._get_counter_value(
                    "llm_errors_total",
                    provider="alibaba_cloud",
                    task_type="extraction",
                    error_type=error_type,
                )
            return count

        rate_limit_count = get_error_count("rate_limit")
        api_error_count = get_error_count("api_error")
        budget_count = get_error_count("budget_exceeded")

        assert rate_limit_count > 0
        assert api_error_count > 0
        assert budget_count > 0

    def _get_counter_value(self, metric_name, **labels):
        """Helper to get counter value by labels."""
        for family in REGISTRY.collect():
            if family.name == metric_name:
                for sample in family.samples:
                    if all(sample.labels.get(k) == v for k, v in labels.items()):
                        return sample.value
        return 0.0


class TestUpdateBudgetMetrics:
    """Test update_budget_metrics function."""

    def test_update_spend_gauge(self):
        """Verify monthly spend gauge updates."""
        # Update budget metrics
        update_budget_metrics(
            provider="alibaba_cloud", monthly_spending=5.25, budget_limit=10.0
        )

        # Verify gauge value
        spend = self._get_gauge_value("monthly_spend_usd", provider="alibaba_cloud")
        assert spend == 5.25

    def test_update_budget_remaining_with_limit(self):
        """Verify budget remaining calculation with limit."""
        # Update with budget limit
        update_budget_metrics(provider="openai", monthly_spending=12.50, budget_limit=20.0)

        # Verify remaining
        remaining = self._get_gauge_value(
            "monthly_budget_remaining_usd", provider="openai"
        )
        assert remaining == 7.50  # 20.0 - 12.50

    def test_update_budget_remaining_unlimited(self):
        """Verify budget remaining with unlimited budget (0.0)."""
        # Update with no limit
        update_budget_metrics(provider="local_ollama", monthly_spending=0.0, budget_limit=0.0)

        # Verify unlimited sentinel
        remaining = self._get_gauge_value(
            "monthly_budget_remaining_usd", provider="local_ollama"
        )
        assert remaining == -1.0  # Sentinel for unlimited

    def test_update_budget_exceeded(self):
        """Verify budget remaining when exceeded."""
        # Update with exceeded budget
        update_budget_metrics(provider="alibaba_cloud", monthly_spending=15.0, budget_limit=10.0)

        # Verify remaining (should be 0.0, not negative)
        remaining = self._get_gauge_value(
            "monthly_budget_remaining_usd", provider="alibaba_cloud"
        )
        assert remaining == 0.0

    def _get_gauge_value(self, metric_name, **labels):
        """Helper to get gauge value by labels."""
        for family in REGISTRY.collect():
            if family.name == metric_name:
                for sample in family.samples:
                    if all(sample.labels.get(k) == v for k, v in labels.items()):
                        return sample.value
        return None


class TestMetricsIntegration:
    """Integration tests for metrics tracking."""

    def test_full_request_lifecycle(self):
        """Test complete request tracking with all metrics."""
        provider = "alibaba_cloud"
        model = "qwen-plus"
        task_type = "extraction"

        # Get initial values (try both metric names)
        initial_requests = self._get_counter_value(
            "llm_requests", provider=provider, task_type=task_type, model=model
        )
        if initial_requests == 0.0:
            initial_requests = self._get_counter_value(
                "llm_requests_total", provider=provider, task_type=task_type, model=model
            )
        initial_cost = self._get_counter_value("llm_cost_usd", provider=provider)

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

        # Verify all metrics updated (try both metric names)
        new_requests = self._get_counter_value(
            "llm_requests", provider=provider, task_type=task_type, model=model
        )
        if new_requests == 0.0:
            new_requests = self._get_counter_value(
                "llm_requests_total", provider=provider, task_type=task_type, model=model
            )
        new_cost = self._get_counter_value("llm_cost_usd", provider=provider)
        spend = self._get_gauge_value("monthly_spend_usd", provider=provider)
        remaining = self._get_gauge_value("monthly_budget_remaining_usd", provider=provider)

        assert new_requests == initial_requests + 1
        assert new_cost >= initial_cost + 0.002
        assert spend == 0.002
        assert remaining == pytest.approx(9.998, rel=1e-3)

    def test_multiple_providers_tracked_separately(self):
        """Test that different providers track metrics independently."""
        # Track requests for different providers
        track_llm_request(
            provider="local_ollama",
            model="llama3.2",
            task_type="generation",
            tokens_used=1000,
            cost_usd=0.0,
            latency_seconds=0.5,
        )

        track_llm_request(
            provider="alibaba_cloud",
            model="qwen-turbo",
            task_type="generation",
            tokens_used=1000,
            cost_usd=0.001,
            latency_seconds=0.8,
        )

        # Verify separate tracking
        local_cost = self._get_counter_value("llm_cost_usd", provider="local_ollama")
        cloud_cost = self._get_counter_value("llm_cost_usd", provider="alibaba_cloud")

        assert local_cost == 0.0  # Local is free
        assert cloud_cost > 0.0  # Cloud has cost

    def _get_counter_value(self, metric_name, **labels):
        """Helper to get counter value by labels."""
        for family in REGISTRY.collect():
            if family.name == metric_name:
                for sample in family.samples:
                    if all(sample.labels.get(k) == v for k, v in labels.items()):
                        return sample.value
        return 0.0

    def _get_gauge_value(self, metric_name, **labels):
        """Helper to get gauge value by labels."""
        for family in REGISTRY.collect():
            if family.name == metric_name:
                for sample in family.samples:
                    if all(sample.labels.get(k) == v for k, v in labels.items()):
                        return sample.value
        return None
