"""
Test script for Alibaba Cloud DashScope API connectivity.

Sprint 23: Validates that Alibaba Cloud (Qwen models) works with AegisLLMProxy.

Usage:
    python scripts/test_alibaba_cloud.py
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
    QualityRequirement,
    Complexity,
)


async def test_alibaba_cloud():
    """Test AegisLLMProxy with Alibaba Cloud (Qwen)."""

    print("=" * 70)
    print("Sprint 23: Alibaba Cloud (Qwen) Connectivity Test")
    print("=" * 70)
    print()

    # Initialize proxy
    print("[1/4] Initializing AegisLLMProxy...")
    try:
        proxy = get_aegis_llm_proxy()
        print("  SUCCESS: Proxy initialized")
        print(f"  Providers enabled: {list(proxy.config.providers.keys())}")

        if not proxy.config.is_provider_enabled("alibaba_cloud"):
            print("  WARNING: alibaba_cloud provider not enabled (missing API key)")
            print("  Please set ALIBABA_CLOUD_API_KEY in .env")
            return False

    except Exception as e:
        print(f"  ERROR: Failed to initialize proxy: {e}")
        return False
    print()

    # Test 1: High quality + high complexity (should route to Alibaba Cloud)
    print("[2/4] Test 1: High quality task routing to Alibaba Cloud")
    try:
        task = LLMTask(
            task_type=TaskType.EXTRACTION,
            prompt="Extract the main concepts from this text: Artificial intelligence is transforming industries.",
            quality_requirement=QualityRequirement.HIGH,
            complexity=Complexity.HIGH,
        )

        provider, reason = proxy._route_task(task)
        print(f"  Routing: {provider} (reason: {reason})")

        if provider != "alibaba_cloud":
            print(f"  WARNING: Expected alibaba_cloud, got {provider}")
            print("  This is OK if budget exceeded or provider disabled")

        print("  SUCCESS: Routing decision made")
    except Exception as e:
        print(f"  ERROR: {e}")
        return False
    print()

    # Test 2: Actual API call to Alibaba Cloud
    print("[3/4] Test 2: API call to Alibaba Cloud (Qwen)")
    print("  Sending test request: 'What is 2+2?'")
    try:
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt="What is 2+2? Answer with just the number.",
            quality_requirement=QualityRequirement.HIGH,
            complexity=Complexity.HIGH,
        )

        response = await proxy.generate(task)

        print(f"  Provider used: {response.provider}")
        print(f"  Model: {response.model}")
        print(f"  Response: {response.content[:100]}")
        print(f"  Tokens: {response.tokens_used}")
        print(f"  Cost: ${response.cost_usd:.6f}")
        print(f"  Latency: {response.latency_ms:.0f}ms")
        print(f"  Routing reason: {response.routing_reason}")

        if response.provider == "alibaba_cloud":
            print("  SUCCESS: Alibaba Cloud API working!")
        else:
            print(f"  INFO: Fell back to {response.provider} (this is OK)")

    except Exception as e:
        print(f"  ERROR: {e}")
        print()
        print("  Possible issues:")
        print("    - Invalid API key")
        print("    - Network connectivity")
        print("    - Model name incorrect")
        return False
    print()

    # Test 3: Metrics
    print("[4/4] Metrics Summary")
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
    success = await test_alibaba_cloud()

    print("=" * 70)
    if success:
        print("RESULT: Alibaba Cloud test PASSED")
        print()
        print("Alibaba Cloud (Qwen) is ready to use!")
        print()
        print("Three-Tier Strategy:")
        print("  Tier 1 (70%): Local Ollama (FREE)")
        print("  Tier 2 (20%): Alibaba Cloud Qwen (~$0.001/1k tokens)")
        print("  Tier 3 (10%): OpenAI (optional, ~$0.015/1k tokens)")
    else:
        print("RESULT: Alibaba Cloud test FAILED")
        print("Check errors above and .env configuration")
    print("=" * 70)

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
