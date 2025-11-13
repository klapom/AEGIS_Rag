"""
List available models on Ollama Cloud.

Sprint 23: Discovers which models are available on Ollama Cloud API.

Usage:
    python scripts/list_ollama_cloud_models.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from any_llm import list_models, LLMProvider

# Load environment variables
load_dotenv()


async def list_available_models():
    """List models available on Ollama Cloud."""

    api_key = os.getenv("OLLAMA_CLOUD_API_KEY")
    base_url = os.getenv("OLLAMA_CLOUD_BASE_URL")

    print("=" * 70)
    print("Ollama Cloud: Available Models")
    print("=" * 70)
    print()

    if not api_key or not base_url:
        print("ERROR: OLLAMA_CLOUD_API_KEY or OLLAMA_CLOUD_BASE_URL not set")
        return False

    print(f"API URL: {base_url}")
    print()

    try:
        print("Fetching available models...")
        models = await list_models(
            provider=LLMProvider.OLLAMA,
            base_url=base_url,
            api_key=api_key,
        )

        print(f"\nFound {len(models)} models:")
        print("-" * 70)

        for model in models:
            if isinstance(model, dict):
                name = model.get("name", model.get("id", "unknown"))
                print(f"  - {name}")
            else:
                print(f"  - {model}")

        print("-" * 70)
        print()
        print("Recommended models for AegisRAG:")
        print("  - llama3-70b (high quality extraction)")
        print("  - llama3.1 (general purpose)")
        print("  - mistral (fast reasoning)")
        print()

        return True

    except Exception as e:
        print(f"ERROR: Failed to list models: {e}")
        print()
        print("This might be because:")
        print("  - Ollama Cloud API doesn't support list_models endpoint")
        print("  - API key/URL incorrect")
        print()
        print("Let's try common model names instead...")
        return False


async def test_common_models():
    """Test common model names directly."""

    from any_llm import acompletion, LLMProvider

    api_key = os.getenv("OLLAMA_CLOUD_API_KEY")
    base_url = os.getenv("OLLAMA_CLOUD_BASE_URL")

    common_models = [
        "llama3.1",
        "llama3-70b",
        "llama3",
        "mistral",
        "mixtral",
        "gemma2",
    ]

    print()
    print("Testing common model names:")
    print("-" * 70)

    for model in common_models:
        print(f"  Testing '{model}'... ", end="", flush=True)

        try:
            response = await acompletion(
                model=model,
                messages=[{"role": "user", "content": "Hi"}],
                provider=LLMProvider.OLLAMA,
                base_url=base_url,
                api_key=api_key,
                max_tokens=5,
            )

            content = response.choices[0].message.content
            print(f"SUCCESS - Response: {content[:30]}...")

        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg or "not found" in error_msg.lower():
                print("NOT FOUND (404)")
            else:
                print(f"ERROR: {str(e)[:50]}")

    print("-" * 70)


async def main():
    """Main function."""
    success = await list_available_models()

    if not success:
        await test_common_models()

    print()
    print("=" * 70)
    print("Next steps:")
    print("  1. Update OLLAMA_CLOUD_BASE_URL if needed")
    print("  2. Use a working model name in config/llm_config.yml")
    print("  3. Re-run: python scripts/test_ollama_cloud.py")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
