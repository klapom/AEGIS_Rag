"""Test script for verifying Prometheus metrics endpoint.

Sprint 24 - Feature 24.1
"""

import sys

# Test 1: Import metrics module
try:
    from src.core.metrics import (
        track_llm_error,
        track_llm_request,
        update_budget_metrics,
    )

    print("SUCCESS: Metrics module imported")
except Exception as e:
    print(f"FAIL: Could not import metrics module: {e}")
    sys.exit(1)

# Test 2: Track sample request
try:
    track_llm_request(
        provider="local_ollama",
        model="test-model",
        task_type="test",
        tokens_used=100,
        cost_usd=0.0,
        latency_seconds=0.5,
    )
    print("SUCCESS: Track request works")
except Exception as e:
    print(f"FAIL: Could not track request: {e}")
    sys.exit(1)

# Test 3: Track error
try:
    track_llm_error(provider="test", task_type="test", error_type="test_error")
    print("SUCCESS: Track error works")
except Exception as e:
    print(f"FAIL: Could not track error: {e}")
    sys.exit(1)

# Test 4: Update budget
try:
    update_budget_metrics(provider="test", monthly_spending=1.0, budget_limit=10.0)
    print("SUCCESS: Update budget works")
except Exception as e:
    print(f"FAIL: Could not update budget: {e}")
    sys.exit(1)

# Test 5: Generate Prometheus format
try:
    from prometheus_client import generate_latest

    metrics_output = generate_latest().decode("utf-8")
    assert "llm_requests" in metrics_output
    assert "llm_cost_usd" in metrics_output
    assert "llm_latency_seconds" in metrics_output
    print("SUCCESS: Prometheus format generation works")
    print("\nSample metrics output (first 500 chars):")
    print(metrics_output[:500])
except Exception as e:
    print(f"FAIL: Could not generate Prometheus format: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("ALL TESTS PASSED - Metrics implementation working correctly!")
print("=" * 60)
print("\nNext steps:")
print("1. Start the API: uvicorn src.api.main:app --reload")
print("2. Access metrics: http://localhost:8000/metrics")
print("3. Set up Prometheus scraping (see docs/guides/MONITORING.md)")
print("4. Import Grafana dashboard: config/grafana/llm_cost_dashboard.json")
