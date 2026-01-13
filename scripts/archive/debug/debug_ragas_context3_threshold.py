"""Find the exact threshold where Context #3 breaks qwen2.5 structured output.

Sprint 75: Systematic debugging of RAGAS parsing failures.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_ollama import ChatOllama
from ragas.metrics._context_precision import ContextPrecisionPrompt, QAC, Verification


async def test_context_length(context: str, length: int, prompt, llm):
    """Test a specific context length."""
    truncated = context[:length]

    test_input = QAC(
        question="What is BGE-M3?",
        context=truncated,
        answer="BGE-M3 is a multilingual embedding model for semantic search with 1024 dimensions.",
    )

    prompt_str = prompt.to_string(test_input)

    try:
        response = await llm.ainvoke(prompt_str)

        # Try to parse
        result = Verification.model_validate_json(response.content)
        return True, result.verdict, len(response.content)
    except Exception as e:
        return False, None, len(response.content) if 'response' in locals() else 0


async def main():
    print("🔍 Finding Context #3 Length Threshold for qwen2.5:7b")
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
    print("\n📥 Retrieving Context #3 from AEGIS RAG...")
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

    print(f"✅ Context #3 retrieved: {len(context3)} chars")
    print(f"Preview: {context3[:100]}...")

    # Create prompt
    prompt = ContextPrecisionPrompt()

    # Test different lengths
    test_lengths = [
        1000,   # Very short
        2500,   # ~Context #1 size
        5000,   # Short
        10000,  # Medium
        15000,  # ~Context #2 size
        20000,  # Large
        25000,  # Very large
        30000,  # Almost full
        len(context3),  # Full context
    ]

    print(f"\n{'='*80}")
    print(f"Testing {len(test_lengths)} different context lengths")
    print(f"{'='*80}\n")

    results_table = []

    for length in test_lengths:
        print(f"⏳ Testing {length:,} chars...", end=" ", flush=True)

        success, verdict, response_len = await test_context_length(
            context3, length, prompt, llm
        )

        results_table.append({
            'length': length,
            'success': success,
            'verdict': verdict,
            'response_len': response_len
        })

        if success:
            print(f"✅ SUCCESS (verdict={verdict}, response={response_len} chars)")
        else:
            print(f"❌ FAILED (response={response_len} chars)")
            # Don't break - continue testing to find pattern

    # Summary
    print(f"\n{'='*80}")
    print("📊 SUMMARY")
    print(f"{'='*80}\n")

    print(f"{'Length':<12} {'Status':<10} {'Verdict':<10} {'Response Len':<15}")
    print("-" * 50)

    for r in results_table:
        status = "✅ SUCCESS" if r['success'] else "❌ FAILED"
        verdict = str(r['verdict']) if r['verdict'] is not None else "N/A"
        print(f"{r['length']:>10,}  {status:<10} {verdict:<10} {r['response_len']:>10,}")

    # Find threshold
    failures = [r for r in results_table if not r['success']]
    if failures:
        first_failure = failures[0]
        print(f"\n🔴 First failure at: {first_failure['length']:,} characters")

        # Try to narrow down
        if len(results_table) > 0:
            last_success = None
            for r in results_table:
                if r['success']:
                    last_success = r
                else:
                    break

            if last_success:
                print(f"✅ Last success at: {last_success['length']:,} characters")
                print(f"\n💡 Threshold appears to be between {last_success['length']:,} and {first_failure['length']:,} chars")
    else:
        print("\n✅ All tests passed! Context #3 should work.")


if __name__ == "__main__":
    asyncio.run(main())
