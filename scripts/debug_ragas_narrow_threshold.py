"""Narrow down exact threshold between 20K-25K chars.

Sprint 75: Find precise failure point for qwen2.5 structured output.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_ollama import ChatOllama
from ragas.metrics._context_precision import ContextPrecisionPrompt, QAC, Verification


async def test_context_and_show_response(context: str, length: int, prompt, llm):
    """Test a specific context length and show the response."""
    truncated = context[:length]

    test_input = QAC(
        question="What is BGE-M3?",
        context=truncated,
        answer="BGE-M3 is a multilingual embedding model for semantic search with 1024 dimensions.",
    )

    prompt_str = prompt.to_string(test_input)

    response = await llm.ainvoke(prompt_str)
    response_text = response.content

    try:
        # Try to parse with Verification model
        result = Verification.model_validate_json(response_text)
        return True, result.verdict, response_text, None
    except Exception as e:
        # Also try raw JSON to see what we got
        try:
            parsed_json = json.loads(response_text)
            return False, None, response_text, parsed_json
        except:
            return False, None, response_text, None


async def main():
    print("🔍 Narrowing Threshold: 20K-25K Characters")
    print("="*80)

    # Create LLM
    llm = ChatOllama(
        model="qwen2.5:7b",
        base_url="http://localhost:11434",
        temperature=0.0,
        num_ctx=8192,
        num_predict=2048,
        format="json",
    )

    # Get Context #3
    print("\n📥 Retrieving Context #3...")
    from src.components.retrieval.four_way_hybrid_search import get_four_way_hybrid_search

    search_engine = get_four_way_hybrid_search()
    results = await search_engine.search(
        query="What is BGE-M3?",
        top_k=5,
        allowed_namespaces=["default"],
        use_reranking=True,
    )

    contexts = [r["text"] for r in results.get("results", [])]
    context3 = contexts[2]
    print(f"✅ Retrieved: {len(context3)} chars\n")

    # Create prompt
    prompt = ContextPrecisionPrompt()

    # Narrow down: test every 1K from 20K to 25K
    test_lengths = [20000, 21000, 22000, 23000, 24000, 25000]

    print(f"{'='*80}")
    print(f"Testing exact threshold")
    print(f"{'='*80}\n")

    for length in test_lengths:
        print(f"\n{'─'*80}")
        print(f"Testing {length:,} chars")
        print(f"{'─'*80}")

        success, verdict, response_text, parsed_json = await test_context_and_show_response(
            context3, length, prompt, llm
        )

        if success:
            print(f"✅ SUCCESS: Pydantic validation passed")
            print(f"   Verdict: {verdict}")
            print(f"   Response: {response_text[:150]}...")
        else:
            print(f"❌ FAILED: Pydantic validation failed")
            print(f"\n📄 Full LLM Response:")
            print(response_text)

            if parsed_json:
                print(f"\n📊 Parsed JSON structure:")
                print(f"   Keys: {list(parsed_json.keys())}")
                for key, value in parsed_json.items():
                    val_preview = str(value)[:100]
                    print(f"   {key}: {val_preview}...")

            # Check if this is first failure
            if length == 21000:
                print(f"\n🔴 EXACT THRESHOLD IDENTIFIED: Between 20,000 and 21,000 characters")
                break

    print(f"\n{'='*80}")


if __name__ == "__main__":
    asyncio.run(main())
