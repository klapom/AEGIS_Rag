"""Test qwen3:8b and gpt-oss:20b with extended 16K context window.

Sprint 75: Verify that 16384 token context window allows 30K+ character contexts.
"""

import asyncio
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_ollama import ChatOllama
from ragas.metrics._context_precision import ContextPrecisionPrompt, QAC, Verification


async def test_model_extended(model_name: str, context: str) -> dict:
    """Test a model with extended context lengths (up to 40K chars).

    Returns:
        dict with test results
    """
    print(f"\n{'='*80}")
    print(f"🔍 Testing Model: {model_name}")
    print(f"   Context Window: 16384 tokens (~65K chars theoretical)")
    print(f"{'='*80}\n")

    # Create LLM with extended context
    try:
        llm = ChatOllama(
            model=model_name,
            base_url="http://localhost:11434",
            temperature=0.0,
            num_ctx=16384,  # DOUBLED from 8192
            num_predict=512,  # REDUCED from 2048
            format="json",
        )
    except Exception as e:
        print(f"❌ Failed to initialize model: {e}")
        return {'model': model_name, 'works': False, 'error': str(e)}

    # Create prompt
    prompt = ContextPrecisionPrompt()

    # Extended test lengths: focus on 20K-40K range
    test_lengths = [
        20000,  # Previous max (should work)
        25000,  # Previously failed
        30000,  # Full Context #3
        35000,  # Beyond any real doc
        40000,  # Stress test
    ]

    results = []
    latencies = []

    for length in test_lengths:
        truncated = context[:length] if len(context) >= length else context

        test_input = QAC(
            question="What is BGE-M3?",
            context=truncated,
            answer="BGE-M3 is a multilingual embedding model for semantic search with 1024 dimensions.",
        )

        prompt_str = prompt.to_string(test_input)

        # Calculate token estimate
        prompt_tokens = len(prompt_str) // 4  # Rough estimate

        print(f"  Testing {length:>6,} chars ({prompt_tokens:>5,} tokens est.)...", end=" ", flush=True)

        try:
            start = time.perf_counter()
            response = await llm.ainvoke(prompt_str)
            latency = (time.perf_counter() - start) * 1000  # ms

            # Try to parse
            result = Verification.model_validate_json(response.content)

            results.append({
                'length': length,
                'success': True,
                'latency_ms': latency,
                'verdict': result.verdict,
                'tokens_est': prompt_tokens
            })
            latencies.append(latency)

            print(f"✅ SUCCESS ({latency:.0f}ms, verdict={result.verdict})")

        except Exception as e:
            error_msg = str(e)[:80]
            results.append({
                'length': length,
                'success': False,
                'latency_ms': 0,
                'error': error_msg,
                'tokens_est': prompt_tokens
            })
            print(f"❌ FAILED ({error_msg}...)")

    # Calculate metrics
    successes = [r for r in results if r['success']]
    success_rate = len(successes) / len(results)

    if successes:
        threshold = max(r['length'] for r in successes)
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        works = True
    else:
        threshold = 0
        avg_latency = 0
        works = False

    print(f"\n  📊 Summary:")
    print(f"     Success Rate: {success_rate*100:.0f}% ({len(successes)}/{len(results)})")
    print(f"     Max Working Length: {threshold:,} chars")
    if avg_latency > 0:
        print(f"     Avg Latency: {avg_latency:.0f}ms")

    return {
        'model': model_name,
        'threshold': threshold,
        'avg_latency_ms': avg_latency,
        'success_rate': success_rate,
        'works': works,
        'results': results
    }


async def main():
    print("🔍 Extended Context Window Test (16K tokens)")
    print("="*80)
    print("\nConfiguration:")
    print("  OLLAMA_NUM_CTX: 16384 tokens (~65K chars)")
    print("  num_predict:    512 tokens (reduced from 2048)")
    print("  Available:      ~14,872 tokens (~59K chars)\n")
    print("Testing Models:")
    print("  1. qwen3:8b     (fastest in previous test)")
    print("  2. gpt-oss:20b  (tied for fastest)")
    print()

    # Get Context #3
    print("📥 Retrieving Context #3 from AEGIS RAG...")
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

    # Extend context3 if needed for 40K test
    if len(context3) < 40000:
        # Duplicate to reach 40K
        extended_context = context3
        while len(extended_context) < 40000:
            extended_context += " " + context3
        context3 = extended_context[:40000]

    print(f"✅ Using context: {len(context3):,} chars\n")

    # Models to test
    models = ["qwen3:8b", "gpt-oss:20b"]

    # Run tests
    print("\n" + "="*80)
    print("TESTING WITH EXTENDED CONTEXT WINDOW")
    print("="*80)

    test_results = []
    for model in models:
        result = await test_model_extended(model, context3)
        test_results.append(result)
        await asyncio.sleep(2)

    # Summary
    print("\n\n" + "="*80)
    print("📊 FINAL RESULTS")
    print("="*80)
    print(f"\n{'Model':<20} {'Max Length':<15} {'Avg Latency':<15} {'Success Rate':<15}")
    print("-" * 70)

    for r in sorted(test_results, key=lambda x: x['threshold'], reverse=True):
        status = "✅" if r['works'] else "❌"
        print(f"{status} {r['model']:<18} {r['threshold']:>6,} chars    {r['avg_latency_ms']:>6.0f}ms         {r['success_rate']*100:>4.0f}%")

    # Detailed breakdown
    print("\n" + "="*80)
    print("📈 Detailed Results by Context Length")
    print("="*80)

    for r in test_results:
        if r['works']:
            print(f"\n{r['model']}:")
            for test in r['results']:
                status = "✅" if test['success'] else "❌"
                tokens = test.get('tokens_est', 0)
                if test['success']:
                    print(f"  {status} {test['length']:>6,} chars ({tokens:>5,} tokens) - {test['latency_ms']:.0f}ms")
                else:
                    print(f"  {status} {test['length']:>6,} chars ({tokens:>5,} tokens) - {test.get('error', 'Unknown')[:50]}")

    # Comparison with previous test
    print("\n" + "="*80)
    print("📊 Improvement vs Previous Test (8K context window)")
    print("="*80)
    print("\n  Previous (8K):  Max 20,000 chars")
    for r in test_results:
        if r['threshold'] > 20000:
            improvement = r['threshold'] - 20000
            pct_increase = (improvement / 20000) * 100
            print(f"  {r['model']:<20} Max {r['threshold']:,} chars (+{improvement:,} / +{pct_increase:.0f}%)")
        else:
            print(f"  {r['model']:<20} Max {r['threshold']:,} chars (NO IMPROVEMENT)")

    print("\n" + "="*80)
    print("✅ Extended Context Window Test Complete!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
