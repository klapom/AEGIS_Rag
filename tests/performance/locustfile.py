"""Locust Load Testing for AegisRAG API.

Feature 28.4: Performance Testing - Load Testing with Locust

This module provides comprehensive load testing scenarios for the AegisRAG API:
1. Search endpoint load testing (vector + hybrid search)
2. Chat endpoint load testing (session-based conversations)
3. Ramp-up stress testing (0 to 100 QPS)

Usage:
    # Scenario 1: 50 QPS sustained for 5 minutes (production baseline)
    locust -f locustfile.py --host=http://localhost:8000 \
           --users 50 --spawn-rate 10 --run-time 5m

    # Scenario 2: Ramp up from 0 to 100 QPS over 2 minutes
    locust -f locustfile.py --host=http://localhost:8000 \
           --users 100 --spawn-rate 1 --run-time 2m

    # Scenario 3: 100 QPS peak for 1 minute (stress test)
    locust -f locustfile.py --host=http://localhost:8000 \
           --users 100 --spawn-rate 50 --run-time 1m

    # Web UI mode (recommended for analysis)
    locust -f locustfile.py --host=http://localhost:8000

    # Headless mode with CSV reports
    locust -f locustfile.py --host=http://localhost:8000 \
           --users 50 --spawn-rate 10 --run-time 5m \
           --headless --csv=results/sprint_28 --html=results/sprint_28.html

Dependencies:
    pip install locust  # Or: poetry add --group dev locust
"""

import json
import random
import uuid

from locust import HttpUser, between, task


class RAGUser(HttpUser):
    """Simulated user for AegisRAG load testing.

    This user performs two types of tasks:
    1. Search queries (weight 3): Direct hybrid search requests
    2. Chat queries (weight 1): Session-based conversational queries

    The wait time between requests is 1-3 seconds to simulate realistic user behavior.
    """

    # Wait 1-3 seconds between requests (realistic user behavior)
    wait_time = between(1, 3)

    # Session ID for chat continuity
    session_id: str

    def on_start(self) -> None:
        """Initialize user session.

        Called when a simulated user starts. Creates a unique session ID for chat continuity.
        """
        self.session_id = str(uuid.uuid4())
        self.client.headers = {"Content-Type": "application/json"}

    @task(3)
    def search_query(self) -> None:
        """Perform a search query (weight 3 - most common operation).

        Tests the /api/v1/retrieval/search endpoint with various queries.
        This represents the most common user operation in the system.

        Expected Latency:
            - p50: ~150ms (50ms vector + 50ms BM25 + 50ms fusion)
            - p95: ~300ms
            - p99: ~500ms
        """
        # Sample queries with varying complexity
        queries = [
            "What is LangGraph?",
            "Explain vector databases",
            "How does hybrid search work?",
            "What is RAG?",
            "Compare vector search and BM25",
            "What are the benefits of graph databases?",
            "Explain episodic memory in AI",
            "How do you implement agent orchestration?",
        ]

        query = random.choice(queries)

        with self.client.post(
            "/api/v1/retrieval/search",
            json={
                "query": query,
                "top_k": 5,
                "search_type": "hybrid",
                "use_reranking": False,  # Disable for baseline performance
            },
            catch_response=True,
            name="/api/v1/retrieval/search [hybrid]",
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "results" in data and len(data["results"]) > 0:
                        response.success()
                    else:
                        response.failure("Empty results")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(1)
    def chat_query(self) -> None:
        """Perform a chat query (weight 1 - less common than search).

        Tests the /api/v1/chat endpoint with session-based conversations.
        This represents multi-turn conversations with memory.

        Expected Latency:
            - p50: ~400ms (150ms search + 200ms LLM generation + 50ms memory)
            - p95: ~800ms
            - p99: ~1200ms
        """
        # Sample chat messages
        messages = [
            "Explain vector databases",
            "What is LangGraph used for?",
            "How do I implement a RAG system?",
            "Tell me about hybrid search",
            "What are the components of AEGIS RAG?",
        ]

        message = random.choice(messages)

        with self.client.post(
            "/api/v1/chat",
            json={"query": message, "session_id": self.session_id},
            catch_response=True,
            name="/api/v1/chat",
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "response" in data or "answer" in data:
                        response.success()
                    else:
                        response.failure("Missing response field")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(0.5)
    def vector_search_only(self) -> None:
        """Perform vector-only search (weight 0.5 - occasional operation).

        Tests pure vector search without BM25 fusion.
        Faster than hybrid search, used for quick lookups.

        Expected Latency:
            - p50: ~70ms
            - p95: ~150ms
            - p99: ~250ms
        """
        queries = [
            "LangGraph architecture",
            "Vector embeddings",
            "Neo4j graph database",
            "Agent orchestration",
        ]

        query = random.choice(queries)

        with self.client.post(
            "/api/v1/retrieval/search",
            json={"query": query, "top_k": 5, "search_type": "vector", "use_reranking": False},
            catch_response=True,
            name="/api/v1/retrieval/search [vector-only]",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(0.2)
    def health_check(self) -> None:
        """Health check endpoint (weight 0.2 - monitoring operation).

        Tests the /health endpoint to ensure system is operational.
        Lightweight operation for monitoring.

        Expected Latency:
            - p50: ~10ms
            - p95: ~20ms
            - p99: ~50ms
        """
        with self.client.get("/health", catch_response=True, name="/health") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


class StressTestUser(HttpUser):
    """Stress test user with higher request rate.

    This user is designed for stress testing scenarios with minimal wait time.
    Use this for testing system limits and breaking points.

    Usage:
        locust -f locustfile.py StressTestUser --host=http://localhost:8000 \
               --users 200 --spawn-rate 50 --run-time 5m
    """

    # Minimal wait time for stress testing
    wait_time = between(0.1, 0.5)

    session_id: str

    def on_start(self) -> None:
        """Initialize stress test user."""
        self.session_id = str(uuid.uuid4())
        self.client.headers = {"Content-Type": "application/json"}

    @task(1)
    def rapid_search(self) -> None:
        """Rapid-fire search requests for stress testing."""
        with self.client.post(
            "/api/v1/retrieval/search",
            json={
                "query": "What is LangGraph?",
                "top_k": 5,
                "search_type": "hybrid",
                "use_reranking": False,
            },
            catch_response=True,
            name="/api/v1/retrieval/search [stress]",
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                # Rate limiting is expected under stress
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


# Test scenarios for different load profiles
class LoadTestScenarios:
    """Predefined load test scenarios.

    Scenario 1: Production Baseline (50 QPS sustained)
        locust -f locustfile.py --host=http://localhost:8000 \
               --users 50 --spawn-rate 10 --run-time 5m \
               --headless --csv=results/baseline_50qps

    Scenario 2: Ramp-up Stress (0 to 100 QPS over 2 minutes)
        locust -f locustfile.py --host=http://localhost:8000 \
               --users 100 --spawn-rate 1 --run-time 2m \
               --headless --csv=results/rampup_100qps

    Scenario 3: Peak Capacity (100 QPS sustained for 1 minute)
        locust -f locustfile.py --host=http://localhost:8000 \
               --users 100 --spawn-rate 50 --run-time 1m \
               --headless --csv=results/peak_100qps

    Scenario 4: Stress Test (200 QPS breaking point)
        locust -f locustfile.py StressTestUser --host=http://localhost:8000 \
               --users 200 --spawn-rate 50 --run-time 5m \
               --headless --csv=results/stress_200qps
    """

    pass


if __name__ == "__main__":
    # This allows running locust directly
    import os
    import sys

    # Add locust CLI arguments
    sys.argv.extend(
        [
            "--host",
            os.getenv("AEGIS_RAG_HOST", "http://localhost:8000"),
            "--users",
            "50",
            "--spawn-rate",
            "10",
        ]
    )

    # Import and run locust
    from locust.main import main

    sys.exit(main())
