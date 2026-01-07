"""Run full RAGAS evaluation with 20 samples.

Sprint 75 Feature 75.1: RAGAS Baseline Evaluation with extended 16K context window.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.ragas_evaluator import RAGASEvaluator, BenchmarkSample


async def main():
    print("="*80)
    print("🎯 AEGIS RAG - Full RAGAS Evaluation (Sprint 75)")
    print("="*80)
    print()
    print("Configuration:")
    print("  Model:        gpt-oss:20b (fastest, 100% success rate)")
    print("  Context:      16K tokens (~59K chars, no truncation needed)")
    print("  Samples:      20")
    print("  Metrics:      4 (Context Precision, Recall, Faithfulness, Relevancy)")
    print("  Namespace:    default")
    print("  Top-K:        5 contexts per query")
    print()
    print("="*80)
    print()

    # Load dataset
    dataset_path = Path("data/benchmarks/sprint_75_evaluation_dataset.jsonl")

    print(f"📥 Loading dataset from: {dataset_path}")

    samples = []
    with open(dataset_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            try:
                data = json.loads(line)
                sample = BenchmarkSample(**data)
                samples.append(sample)
            except Exception as e:
                print(f"⚠️  Warning: Failed to parse line {line_num}: {e}")

    print(f"✅ Loaded {len(samples)} samples")
    print()

    # Show sample breakdown
    intents = {}
    difficulties = {}
    for s in samples:
        intent = s.metadata.get('intent', 'unknown')
        difficulty = s.metadata.get('difficulty', 'unknown')
        intents[intent] = intents.get(intent, 0) + 1
        difficulties[difficulty] = difficulties.get(difficulty, 0) + 1

    print("📊 Dataset Breakdown:")
    print(f"   By Intent:     {dict(intents)}")
    print(f"   By Difficulty: {dict(difficulties)}")
    print()

    # Create evaluator
    print("🔧 Initializing RAGAS Evaluator...")
    evaluator = RAGASEvaluator(
        namespace="default",
        llm_model="gpt-oss:20b",  # Sprint 75: Best performer (9s avg, 100% success)
        embedding_model="bge-m3:latest",  # Ignored, uses native service
        metrics=["context_precision", "context_recall", "faithfulness", "answer_relevancy"]
    )
    print("✅ Evaluator initialized")
    print()

    # Run evaluation
    print("="*80)
    print("🚀 Starting RAGAS Evaluation...")
    print("="*80)
    print()

    start_time = datetime.now()

    try:
        results = await evaluator.evaluate_rag_pipeline(
            dataset=samples,
            sample_size=len(samples),  # All 20 samples
            batch_size=10,
            top_k=5,
        )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print()
        print("="*80)
        print("✅ RAGAS Evaluation Complete!")
        print("="*80)
        print()

        # Display results
        print("📊 Overall Metrics:")
        print(f"   Context Precision:  {results.overall_metrics.context_precision:.3f}")
        print(f"   Context Recall:     {results.overall_metrics.context_recall:.3f}")
        print(f"   Faithfulness:       {results.overall_metrics.faithfulness:.3f}")
        print(f"   Answer Relevancy:   {results.overall_metrics.answer_relevancy:.3f}")
        print()

        print(f"📈 Performance:")
        print(f"   Total Samples:      {results.sample_count}")
        print(f"   Duration:           {duration:.1f}s ({duration/60:.1f} minutes)")
        print(f"   Avg per Sample:     {duration/results.sample_count:.1f}s")
        print()

        # Per-intent breakdown
        if results.per_intent_metrics:
            print("📋 Per-Intent Breakdown:")
            print(f"   {'Intent':<15} {'Samples':<10} {'CP':<8} {'CR':<8} {'Faith':<8} {'AR':<8}")
            print("   " + "-"*65)
            for im in results.per_intent_metrics:
                print(f"   {im.intent:<15} {im.sample_count:<10} "
                      f"{im.metrics.context_precision:<8.3f} "
                      f"{im.metrics.context_recall:<8.3f} "
                      f"{im.metrics.faithfulness:<8.3f} "
                      f"{im.metrics.answer_relevancy:<8.3f}")
            print()

        # Generate report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = Path(f"data/evaluation_results/sprint_75_ragas_{timestamp}.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"💾 Saving detailed report to: {report_path}")
        report = evaluator.generate_report(results, output_path=report_path)
        print("✅ Report saved")
        print()

        # Success criteria check
        print("="*80)
        print("🎯 Success Criteria Check (Sprint 75 Targets)")
        print("="*80)
        print()

        targets = {
            "context_precision": 0.75,
            "context_recall": 0.70,
            "faithfulness": 0.90,
            "answer_relevancy": 0.80,
        }

        all_passed = True
        for metric, target in targets.items():
            actual = getattr(results.overall_metrics, metric)
            passed = actual >= target
            status = "✅" if passed else "❌"

            if not passed:
                all_passed = False

            print(f"   {status} {metric.replace('_', ' ').title():<25} "
                  f"Target: {target:.2f}   Actual: {actual:.3f}   "
                  f"{'PASS' if passed else 'FAIL'}")

        print()
        if all_passed:
            print("🎉 All metrics meet or exceed targets!")
        else:
            print("⚠️  Some metrics below target - see improvement recommendations in report")
        print()

        return results

    except Exception as e:
        print()
        print("="*80)
        print("❌ RAGAS Evaluation Failed!")
        print("="*80)
        print()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    results = asyncio.run(main())

    if results:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure
