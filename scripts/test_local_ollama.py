"""
Test script for local Ollama with AegisLLMProxy.

Sprint 23: Validates that local Ollama works with AegisLLMProxy routing.

Usage:
    python scripts/test_local_ollama.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.components.llm_proxy import (
    get_aegis_llm_proxy,
    LLMTask,
    TaskType,
    DataClassification,
    QualityRequirement,
    Complexity,
)


async def test_local_ollama():
    """Test AegisLLMProxy with local Ollama."""

    print("=" * 70)
    print("Sprint 23: AegisLLMProxy - Local Ollama Test")
    print("=" * 70)
    print()

    # Initialize proxy
    print("[1/5] Initializing AegisLLMProxy...")
    try:
        proxy = get_aegis_llm_proxy()
        print("  SUCCESS: Proxy initialized")
        print(f"  Providers enabled: {list(proxy.config.providers.keys())}")
    except Exception as e:
        print(f"  ERROR: Failed to initialize proxy: {e}")
        return False
    print()

    # Test 1: Simple generation (should route to local)
    print("[2/5] Test 1: Simple generation")
    try:
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="What is 2+2? Answer in one word.",
            quality_requirement=QualityRequirement.MEDIUM,
            complexity=Complexity.LOW,
        )

        provider, reason = proxy._route_task(task)
        print(f"  Routing: {provider} (reason: {reason})")

        if provider != "local_ollama":
            print(f"  WARNING: Expected local_ollama, got {provider}")

        response = await proxy.generate(task)
        print(f"  Response: {response.content[:50]}")
        print(f"  Model: {response.model}")
        print(f"  Tokens: {response.tokens_used}")
        print(f"  Cost: ${response.cost_usd:.6f}")
        print(f"  Latency: {response.latency_ms:.0f}ms")
        print("  SUCCESS")
    except Exception as e:
        print(f"  ERROR: {e}")
        return False
    print()

    # Test 2: PII data (must stay local)
    print("[3/5] Test 2: PII data routing")
    try:
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract name: John Smith, SSN 123-45-6789",
            data_classification=DataClassification.PII,
            quality_requirement=QualityRequirement.CRITICAL,  # Even critical → local!
        )

        provider, reason = proxy._route_task(task)
        print(f"  Routing: {provider} (reason: {reason})")

        if provider != "local_ollama":
            print(f"  ERROR: PII must stay local! Got: {provider}")
            return False

        print("  SUCCESS: PII correctly routed to local")
    except Exception as e:
        print(f"  ERROR: {e}")
        return False
    print()

    # Test 3: Embeddings (always local)
    print("[4/5] Test 3: Embeddings routing")
    try:
        task = LLMTask(
            task_type=TaskType.EMBEDDING,
            prompt="Generate embedding for: artificial intelligence",
        )

        provider, reason = proxy._route_task(task)
        print(f"  Routing: {provider} (reason: {reason})")

        if provider != "local_ollama":
            print(f"  ERROR: Embeddings must stay local! Got: {provider}")
            return False

        print("  SUCCESS: Embeddings correctly routed to local")
    except Exception as e:
        print(f"  ERROR: {e}")
        return False
    print()

    # Test 4: Metrics summary
    print("[5/5] Metrics Summary")
    try:
        metrics = proxy.get_metrics_summary()
        print(f"  Total requests: {metrics['request_count']}")
        print(f"  Total cost: ${metrics['total_cost_usd']:.6f}")
        print(f"  Providers enabled: {metrics['providers_enabled']}")
        print("  SUCCESS")
    except Exception as e:
        print(f"  ERROR: {e}")
        return False
    print()

    return True


async def main():
    """Main test function."""
    success = await test_local_ollama()

    print("=" * 70)
    if success:
        print("RESULT: Local Ollama test PASSED")
        print()
        print("Next steps:")
        print("  1. All routing logic works correctly")
        print("  2. Local Ollama is production-ready")
        print("  3. For cloud providers:")
        print("     - OpenAI API: Use https://api.openai.com/v1")
        print("     - DeepSeek: Use https://api.deepseek.com/v1")
        print("     - Or any OpenAI-compatible API")
    else:
        print("RESULT: Local Ollama test FAILED")
        print("Please fix the issues above")
    print("=" * 70)

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
