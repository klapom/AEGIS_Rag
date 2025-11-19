"""
Test script for Ollama Cloud API connectivity.

Sprint 23: Validates that Ollama Cloud API key and URL are configured correctly.

Usage:
    python scripts/test_ollama_cloud.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_ollama_cloud():
    """Test Ollama Cloud API connectivity."""

    # Check environment variables
    api_key = os.getenv("OLLAMA_CLOUD_API_KEY")
    base_url = os.getenv("OLLAMA_CLOUD_BASE_URL")

    print("=" * 70)
    print("Sprint 23: Ollama Cloud API Connectivity Test")
    print("=" * 70)
    print()

    # Step 1: Validate environment variables
    print("[1/3] Checking environment variables...")
    if not api_key:
        print("ERROR: OLLAMA_CLOUD_API_KEY not set in .env")
        print("Please add your Ollama Cloud API key to .env file")
        return False

    if not base_url:
        print("ERROR: OLLAMA_CLOUD_BASE_URL not set in .env")
        print("Please add Ollama Cloud base URL to .env file")
        return False

    print(f"  API Key: {'*' * 20}{api_key[-8:]} (masked)")
    print(f"  Base URL: {base_url}")
    print("  SUCCESS: Environment variables configured")
    print()

    # Step 2: Test ANY-LLM import
    print("[2/3] Testing ANY-LLM SDK import...")
    try:
        from any_llm import LLMProvider, acompletion

        print("  SUCCESS: ANY-LLM SDK imported")
    except ImportError as e:
        print(f"  ERROR: Failed to import ANY-LLM SDK: {e}")
        print("  Run: poetry install")
        return False
    print()

    # Step 3: Test Ollama Cloud API call
    print("[3/3] Testing Ollama Cloud API call...")
    print("  Sending test request: 'What is 2+2?'")
    print()

    # Try multiple approaches
    test_cases = [
        {
            "name": "Approach 1: OLLAMA provider with api_base",
            "provider": LLMProvider.OLLAMA,
            "api_base": base_url,
            "api_key": api_key,
        },
        {
            "name": "Approach 2: OPENAI provider with Ollama URL",
            "provider": LLMProvider.OPENAI,
            "api_base": base_url,
            "api_key": api_key,
        },
        {
            "name": "Approach 3: OLLAMA provider with base_url kwarg",
            "provider": LLMProvider.OLLAMA,
            "base_url": base_url,
            "api_key": api_key,
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"  [{i}/3] {test_case['name']}...")

        try:
            # Prepare kwargs
            kwargs = {
                "model": "llama3.2",
                "messages": [{"role": "user", "content": "What is 2+2? Answer in one word."}],
                "provider": test_case["provider"],
                "max_tokens": 20,
                "temperature": 0.0,
            }

            # Add api_base or base_url
            if "api_base" in test_case:
                kwargs["api_base"] = test_case["api_base"]
            if "base_url" in test_case:
                kwargs["base_url"] = test_case["base_url"]
            if "api_key" in test_case:
                kwargs["api_key"] = test_case["api_key"]

            response = await acompletion(**kwargs)

            # Extract response content
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if hasattr(response, "usage") else 0

            print(f"        Response: {content}")
            print(f"        Tokens used: {tokens_used}")
            print(f"        SUCCESS!")
            print()

            # Calculate approximate cost
            cost = tokens_used * 0.000001  # $0.001 per 1k tokens
            print(f"  Estimated cost: ${cost:.6f}")
            print()
            print(f"  WINNER: {test_case['name']} works!")
            return True

        except Exception as e:
            print(f"        FAILED: {str(e)[:80]}...")
            print()
            continue

    print("  ERROR: All approaches failed")
    print()
    print("  Possible issues:")
    print("    - Invalid API key")
    print("    - Incorrect base URL (try https://ollama.ai or https://cloud.ollama.com)")
    print("    - Network connectivity issue")
    print("    - Ollama Cloud service unavailable")
    print()
    return False


async def main():
    """Main test function."""
    success = await test_ollama_cloud()

    print("=" * 70)
    if success:
        print("RESULT: Ollama Cloud connectivity test PASSED")
        print("You can now use Ollama Cloud in AegisLLMProxy!")
    else:
        print("RESULT: Ollama Cloud connectivity test FAILED")
        print("Please fix the issues above before using Ollama Cloud")
    print("=" * 70)

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
