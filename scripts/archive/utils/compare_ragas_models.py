"""Compare different LLM models for RAGAS evaluation.

Sprint 75: Test qwen3:32b, nemotron-no-think, gpt-oss:20b, qwen3:8b
for structured output reliability with RAGAS Context Precision.
"""

import asyncio
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_ollama import ChatOllama
from ragas.metrics._context_precision import ContextPrecisionPrompt, QAC, Verification


async def test_model_with_context3(model_name: str, context: str) -> dict:
    """Test a specific model with Context #3 at various lengths.

    Returns:
        dict with test results: {
            'model': str,
            'threshold': int,  # Max length that works
            'avg_latency_ms': float,
            'success_rate': float,
            'works': bool
        }
    """
    print(f"\n{'='*80}")
    print(f"🔍 Testing Model: {model_name}")
    print(f"{'='*80}\n")

    # Create LLM
    try:
        llm = ChatOllama(
            model=model_name,
            base_url="http://localhost:11434",
            temperature=0.0,
            num_ctx=8192,
            num_predict=2048,
            format="json",
        )
    except Exception as e:
        print(f"❌ Failed to initialize model: {e}")
        return {
            'model': model_name,
            'threshold': 0,
            'avg_latency_ms': 0,
            'success_rate': 0.0,
            'works': False,
            'error': str(e)
        }

    # Create prompt
    prompt = ContextPrecisionPrompt()

    # Test different lengths (quick test: 5K, 10K, 20K, 25K, 30K)
    test_lengths = [5000, 10000, 20000, 25000, 30000]
    results = []
    latencies = []

    for length in test_lengths:
        truncated = context[:length]

        test_input = QAC(
            question="What is BGE-M3?",
            context=truncated,
            answer="BGE-M3 is a multilingual embedding model for semantic search with 1024 dimensions.",
        )

        prompt_str = prompt.to_string(test_input)

        print(f"  Testing {length:>6,} chars...", end=" ", flush=True)

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
                'verdict': result.verdict
            })
            latencies.append(latency)

            print(f"✅ SUCCESS ({latency:.0f}ms, verdict={result.verdict})")

        except Exception as e:
            results.append({
                'length': length,
                'success': False,
                'latency_ms': 0,
                'error': str(e)[:50]
            })
            print(f"❌ FAILED ({str(e)[:50]}...)")

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


async def test_full_ragas_metrics(model_name: str) -> dict:
    """Test all 4 RAGAS metrics with a working model.

    Returns:
        dict with timing for each metric
    """
    print(f"\n{'='*80}")
    print(f"📊 Testing All 4 RAGAS Metrics: {model_name}")
    print(f"{'='*80}\n")

    from src.evaluation.ragas_evaluator import BenchmarkSample, RAGASEvaluator

    # Create evaluator with this model
    evaluator = RAGASEvaluator(
        namespace="default",
        llm_model=model_name,
    )

    # Create single test sample
    test_sample = BenchmarkSample(
        question="What is BGE-M3?",
        ground_truth="BGE-M3 is a 1024-dimensional multilingual embedding model from BAAI used for semantic search.",
        contexts=[],  # Will be retrieved
        answer="",    # Will be generated
        metadata={"intent": "factual"}
    )

    print(f"🏃 Running full RAGAS evaluation (1 sample, 4 metrics)...\n")

    try:
        start = time.perf_counter()
        results = await evaluator.evaluate_rag_pipeline(
            dataset=[test_sample],
            sample_size=1,
            top_k=5,
        )
        total_time = time.perf_counter() - start

        print(f"\n✅ RAGAS Evaluation Complete!")
        print(f"\n   Metrics:")
        print(f"     Context Precision:  {results.overall_metrics.context_precision:.3f}")
        print(f"     Context Recall:     {results.overall_metrics.context_recall:.3f}")
        print(f"     Faithfulness:       {results.overall_metrics.faithfulness:.3f}")
        print(f"     Answer Relevancy:   {results.overall_metrics.answer_relevancy:.3f}")
        print(f"\n   Duration: {total_time:.1f}s")

        return {
            'model': model_name,
            'success': True,
            'total_time_s': total_time,
            'context_precision': results.overall_metrics.context_precision,
            'context_recall': results.overall_metrics.context_recall,
            'faithfulness': results.overall_metrics.faithfulness,
            'answer_relevancy': results.overall_metrics.answer_relevancy,
        }

    except Exception as e:
        print(f"\n❌ RAGAS Evaluation Failed: {e}")
        return {
            'model': model_name,
            'success': False,
            'error': str(e)
        }


async def main():
    print("🔍 RAGAS Model Comparison Test")
    print("="*80)
    print("\nTesting Models:")
    print("  1. qwen3:32b        (20 GB)")
    print("  2. nemotron-no-think (24 GB)")
    print("  3. gpt-oss:20b      (13 GB)")
    print("  4. qwen3:8b         (5.2 GB)")
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
    print(f"✅ Retrieved Context #3: {len(context3):,} chars\n")

    # Models to test
    models = [
        "qwen3:32b",
        "nemotron-no-think:latest",
        "gpt-oss:20b",
        "qwen3:8b",
    ]

    # Phase 1: Test threshold with Context #3
    print("\n" + "="*80)
    print("PHASE 1: Testing Structured Output Threshold")
    print("="*80)

    threshold_results = []
    for model in models:
        result = await test_model_with_context3(model, context3)
        threshold_results.append(result)

        # Small delay between models to avoid overwhelming Ollama
        await asyncio.sleep(2)

    # Phase 2: Test full RAGAS metrics with working models
    print("\n\n" + "="*80)
    print("PHASE 2: Full RAGAS Evaluation (All 4 Metrics)")
    print("="*80)

    working_models = [r for r in threshold_results if r['works'] and r['threshold'] >= 20000]

    if not working_models:
        print("\n⚠️  No models passed the 20K threshold test!")
        print("    Cannot proceed with full RAGAS evaluation.")
    else:
        print(f"\n✅ {len(working_models)} model(s) passed threshold test:")
        for r in working_models:
            print(f"   - {r['model']}: {r['threshold']:,} chars, {r['avg_latency_ms']:.0f}ms avg")

    ragas_results = []
    for result in working_models:
        ragas_result = await test_full_ragas_metrics(result['model'])
        ragas_results.append(ragas_result)

        # Delay between evaluations
        await asyncio.sleep(2)

    # Final Summary
    print("\n\n" + "="*80)
    print("📊 FINAL RESULTS SUMMARY")
    print("="*80)

    print("\n1️⃣  Structured Output Threshold Test:")
    print("-" * 80)
    print(f"{'Model':<25} {'Max Length':<15} {'Avg Latency':<15} {'Success Rate':<15}")
    print("-" * 80)

    for r in sorted(threshold_results, key=lambda x: x['threshold'], reverse=True):
        status = "✅" if r['works'] else "❌"
        print(f"{status} {r['model']:<23} {r['threshold']:>6,} chars    {r['avg_latency_ms']:>6.0f}ms         {r['success_rate']*100:>4.0f}%")

    if ragas_results:
        print("\n2️⃣  Full RAGAS Evaluation (4 Metrics):")
        print("-" * 80)
        print(f"{'Model':<25} {'CP':<8} {'CR':<8} {'Faith':<8} {'AR':<8} {'Time':<10}")
        print("-" * 80)

        for r in ragas_results:
            if r['success']:
                print(f"✅ {r['model']:<23} "
                      f"{r['context_precision']:>6.3f}  "
                      f"{r['context_recall']:>6.3f}  "
                      f"{r['faithfulness']:>6.3f}  "
                      f"{r['answer_relevancy']:>6.3f}  "
                      f"{r['total_time_s']:>6.1f}s")
            else:
                print(f"❌ {r['model']:<23} FAILED: {r.get('error', 'Unknown')[:40]}")

        print("\n    CP = Context Precision, CR = Context Recall")
        print("    Faith = Faithfulness, AR = Answer Relevancy")

    print("\n" + "="*80)
    print("✅ Model Comparison Complete!")
    print("="*80)

    # Return results for analysis
    return {
        'threshold_results': threshold_results,
        'ragas_results': ragas_results
    }


if __name__ == "__main__":
    asyncio.run(main())
