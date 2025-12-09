"""Integration tests for Intent Classification with real Ollama LLM.

Sprint 4 Feature 4.2: Query Router & Intent Classification (Real LLM)
Tests cover:
- Real LLM-based intent classification using llama3.2:3b
- Classification accuracy on diverse queries
- Performance and latency tracking
- Error handling with real service failures

Prerequisites:
- Ollama running on localhost:11434
- llama3.2:3b model pulled (ollama pull llama3.2:3b)

Note: These tests require real Ollama/LLM and are skipped in CI.
Run locally with: pytest tests/integration/test_router_integration.py -v
"""

import asyncio
import time

import pytest

# Mark all tests in this module as requiring real LLM
pytestmark = pytest.mark.requires_llm

from src.agents.router import (
    IntentClassifier,
    QueryIntent,
    route_query,
)
from src.agents.state import create_initial_state

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def real_classifier():
    """Create IntentClassifier with real Ollama connection."""
    return IntentClassifier(
        model_name="llama3.2:3b",
        base_url="http://localhost:11434",
        temperature=0.0,  # Deterministic for testing
        max_tokens=50,
    )


@pytest.fixture(scope="module")
async def verify_ollama_available(real_classifier):
    """Verify Ollama is running and model is available."""
    try:
        # Simple test query
        await real_classifier.classify_intent("test query")
        return True
    except Exception as e:
        pytest.skip(f"Ollama not available: {e}")


# ============================================================================
# Integration Tests: Real LLM Classification
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestIntentClassificationRealLLM:
    """Test intent classification with real Ollama LLM."""

    async def test_vector_intent_classification(self, real_classifier, verify_ollama_available):
        """Test LLM correctly classifies vector search queries."""
        queries = [
            "What is retrieval augmented generation?",
            "Explain the concept of embeddings",
            "Find documents about machine learning",
            "Search for information on LangChain",
        ]

        for query in queries:
            intent = await real_classifier.classify_intent(query)
            # Vector or Hybrid are both acceptable for simple semantic queries
            assert intent in [
                QueryIntent.VECTOR,
                QueryIntent.HYBRID,
            ], f"Query '{query}' got unexpected intent: {intent}"

    async def test_graph_intent_classification(self, real_classifier, verify_ollama_available):
        """Test LLM correctly classifies graph-based queries."""
        queries = [
            "How are documents connected to each other?",
            "What is the relationship between RAG and embeddings?",
            "Show me the knowledge graph structure",
            "Find related concepts to vector search",
        ]

        for query in queries:
            intent = await real_classifier.classify_intent(query)
            # Graph or Hybrid are acceptable for relationship queries
            assert intent in [
                QueryIntent.GRAPH,
                QueryIntent.HYBRID,
            ], f"Query '{query}' got unexpected intent: {intent}"

    async def test_hybrid_intent_classification(self, real_classifier, verify_ollama_available):
        """Test LLM correctly classifies hybrid queries."""
        queries = [
            "Find technical documents about RAG and explain the relationships",
            "Search for LangChain docs and show how they relate",
            "What are the connections between vector search and graph RAG?",
        ]

        for query in queries:
            intent = await real_classifier.classify_intent(query)
            # Hybrid is expected, but VECTOR/GRAPH also acceptable
            assert intent in [
                QueryIntent.VECTOR,
                QueryIntent.GRAPH,
                QueryIntent.HYBRID,
            ], f"Query '{query}' got unexpected intent: {intent}"

    async def test_memory_intent_classification(self, real_classifier, verify_ollama_available):
        """Test LLM correctly classifies memory/conversation queries."""
        queries = [
            "What did we discuss previously?",
            "Summarize our conversation so far",
            "What was my last question?",
            "Remind me what you told me about RAG",
        ]

        for query in queries:
            intent = await real_classifier.classify_intent(query)
            # Memory or Hybrid are acceptable
            assert intent in [
                QueryIntent.MEMORY,
                QueryIntent.HYBRID,
            ], f"Query '{query}' got unexpected intent: {intent}"

    async def test_classification_consistency(self, real_classifier, verify_ollama_available):
        """Test that same query gets consistent classification."""
        query = "What is vector search?"

        # Run classification 3 times
        intents = []
        for _ in range(3):
            intent = await real_classifier.classify_intent(query)
            intents.append(intent)

        # With temperature=0.0, should be deterministic
        assert len(set(intents)) == 1, f"Inconsistent intents: {intents}"

    async def test_classification_latency(self, real_classifier, verify_ollama_available):
        """Test that LLM classification completes within performance target."""
        query = "Find documents about RAG"

        start_time = time.perf_counter()
        intent = await real_classifier.classify_intent(query)
        latency_ms = (time.perf_counter() - start_time) * 1000

        # Should complete within 2 seconds for local LLM
        assert latency_ms < 2000, f"Classification took {latency_ms:.2f}ms (>2000ms)"
        assert intent != QueryIntent.UNKNOWN, "Should classify successfully"

    async def test_concurrent_classifications(self, real_classifier, verify_ollama_available):
        """Test concurrent LLM requests work correctly."""
        queries = [
            "What is RAG?",
            "How are documents related?",
            "Search for embeddings info",
            "Show conversation history",
        ]

        # Run all classifications concurrently
        tasks = [real_classifier.classify_intent(q) for q in queries]
        results = await asyncio.gather(*tasks)

        # All should return valid intents
        for intent in results:
            assert intent in [
                QueryIntent.VECTOR,
                QueryIntent.GRAPH,
                QueryIntent.HYBRID,
                QueryIntent.MEMORY,
            ], f"Got invalid intent: {intent}"

    async def test_error_handling_invalid_model(self, verify_ollama_available):
        """Test graceful handling when model doesn't exist."""
        classifier = IntentClassifier(
            model_name="nonexistent-model:latest",
            base_url="http://localhost:11434",
        )

        # Should fallback to HYBRID on error
        intent = await classifier.classify_intent("test query")
        assert intent == QueryIntent.HYBRID, "Should fallback to HYBRID on error"

    async def test_error_handling_wrong_url(self):
        """Test graceful handling when Ollama URL is wrong."""
        classifier = IntentClassifier(
            model_name="llama3.2:3b",
            base_url="http://localhost:9999",  # Wrong port
        )

        # Should fallback to HYBRID on connection error
        intent = await classifier.classify_intent("test query")
        assert intent == QueryIntent.HYBRID, "Should fallback to HYBRID on error"


# ============================================================================
# Integration Tests: Router Node with Real LLM
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestRouterNodeRealLLM:
    """Test route_query node function with real LLM."""

    async def test_route_query_updates_state_with_real_intent(
        self, real_classifier, verify_ollama_available
    ):
        """Test that route_query updates state with real LLM classification."""
        # Monkey-patch the global classifier
        import src.agents.router as router_module

        original_classifier = router_module._classifier
        router_module._classifier = real_classifier

        try:
            state = create_initial_state("What is vector search?")
            result_state = await route_query(state)

            # Check state was updated with real intent
            assert "intent" in result_state, "Intent should be set in state"
            assert result_state["intent"] in [
                "vector",
                "hybrid",
            ], f"Unexpected intent: {result_state['intent']}"

            # Check metadata
            assert "metadata" in result_state, "Metadata should be present"
            assert "agent_path" in result_state["metadata"], "Agent path should be tracked"
            assert "router" in result_state["metadata"]["agent_path"]

        finally:
            # Restore original classifier
            router_module._classifier = original_classifier

    async def test_route_query_performance(self, real_classifier, verify_ollama_available):
        """Test route_query completes within performance target with real LLM."""
        import src.agents.router as router_module

        original_classifier = router_module._classifier
        router_module._classifier = real_classifier

        try:
            state = create_initial_state("Find RAG documentation")

            start_time = time.perf_counter()
            result_state = await route_query(state)
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Should complete within 2 seconds
            assert latency_ms < 2000, f"Router node took {latency_ms:.2f}ms (>2000ms)"
            assert result_state["intent"] != "unknown", "Should classify successfully"

        finally:
            router_module._classifier = original_classifier


# ============================================================================
# Integration Tests: Classification Accuracy Benchmarks
# ============================================================================


@pytest.mark.integration
@pytest.mark.asyncio
class TestClassificationAccuracyBenchmark:
    """Benchmark classification accuracy on diverse queries."""

    @pytest.fixture
    def test_cases(self):
        """Diverse test cases with expected intent categories."""
        return [
            # Vector queries (semantic search)
            ("What is RAG?", [QueryIntent.VECTOR, QueryIntent.HYBRID]),
            ("Explain embeddings", [QueryIntent.VECTOR, QueryIntent.HYBRID]),
            ("Find LangChain docs", [QueryIntent.VECTOR, QueryIntent.HYBRID]),
            # Graph queries (relationships)
            ("How are RAG and LLMs related?", [QueryIntent.GRAPH, QueryIntent.HYBRID]),
            ("Show document connections", [QueryIntent.GRAPH, QueryIntent.HYBRID]),
            # Hybrid queries (both)
            (
                "Search for vector databases and their relationships",
                [QueryIntent.HYBRID, QueryIntent.VECTOR, QueryIntent.GRAPH],
            ),
            # Memory queries (conversation)
            ("What did I ask before?", [QueryIntent.MEMORY, QueryIntent.HYBRID]),
            ("Summarize our chat", [QueryIntent.MEMORY, QueryIntent.HYBRID]),
        ]

    async def test_accuracy_benchmark(self, real_classifier, verify_ollama_available, test_cases):
        """Run accuracy benchmark on diverse queries."""
        correct = 0
        total = len(test_cases)

        results = []
        for query, acceptable_intents in test_cases:
            intent = await real_classifier.classify_intent(query)
            is_correct = intent in acceptable_intents
            if is_correct:
                correct += 1

            results.append(
                {
                    "query": query,
                    "intent": intent.value,
                    "acceptable": [i.value for i in acceptable_intents],
                    "correct": is_correct,
                }
            )

        accuracy = (correct / total) * 100

        # Print benchmark results
        print(f"\n{'='*70}")
        print("Intent Classification Accuracy Benchmark (Real LLM)")
        print(f"{'='*70}")
        print("Model: llama3.2:3b")
        print("Temperature: 0.0")
        print(f"Total queries: {total}")
        print(f"Correct: {correct}")
        print(f"Accuracy: {accuracy:.1f}%")
        print("\nDetailed Results:")
        for r in results:
            status = "✓" if r["correct"] else "✗"
            print(f"{status} {r['query'][:50]:50} → {r['intent']:8} (expected: {r['acceptable']})")
        print(f"{'='*70}\n")

        # We expect at least 75% accuracy (6/8 correct)
        assert accuracy >= 75.0, f"Accuracy {accuracy:.1f}% below 75% threshold"
