"""RAGAS evaluation with gpt-oss:120b - Sprint 124."""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.ragas_evaluator import RAGASEvaluator, BenchmarkSample


async def main():
    print("=" * 70)
    print("🔬 RAGAS Evaluation - gpt-oss:120b (Sprint 124)")
    print("=" * 70)
    print()

    # Load questions
    questions_file = Path(__file__).parent.parent / "data/evaluation/ragas_phase1_questions.jsonl"

    if not questions_file.exists():
        print(f"❌ Questions file not found: {questions_file}")
        return

    # Load first 20 questions for initial test
    questions = []
    with open(questions_file, "r") as f:
        for i, line in enumerate(f):
            if i >= 20:  # Start with 20 questions
                break
            q = json.loads(line)
            questions.append(q)

    print(f"📂 Loaded {len(questions)} questions from {questions_file.name}")
    print()

    # Convert to BenchmarkSample format
    samples = []
    for q in questions:
        sample = BenchmarkSample(
            question=q["question"],
            ground_truth=q["ground_truth"],
            contexts=[],  # Will be retrieved
            answer="",    # Will be generated
            metadata={
                "id": q["id"],
                "doc_type": q.get("doc_type", "unknown"),
                "question_type": q.get("question_type", "unknown"),
                "difficulty": q.get("difficulty", "unknown"),
                "answerable": q.get("answerable", True),
            }
        )
        samples.append(sample)

    # Show sample questions
    print("📋 Sample questions:")
    for i, s in enumerate(samples[:3]):
        print(f"   {i+1}. {s.question[:70]}...")
    print(f"   ... and {len(samples) - 3} more")
    print()

    # Initialize evaluator with gpt-oss:120b
    print("🔧 Initializing RAGAS Evaluator with gpt-oss:120b...")
    evaluator = RAGASEvaluator(
        namespace="ragas_phase1",      # Use phase1 namespace
        llm_model="gpt-oss:120b",      # Use gpt-oss:120b for evaluation
        embedding_model="bge-m3:latest",
    )
    print(f"   ✅ Namespace: {evaluator.namespace}")
    print(f"   ✅ LLM: {evaluator.llm_model}")
    print()

    # Run evaluation
    start_time = datetime.now()
    print(f"🚀 Starting RAGAS evaluation on {len(samples)} samples...")
    print(f"   Started at: {start_time.strftime('%H:%M:%S')}")
    print()

    try:
        # Run full evaluation using evaluate_rag_pipeline
        results = await evaluator.evaluate_rag_pipeline(
            dataset=samples,
            sample_size=None,   # Evaluate all 20
            top_k=10,           # Retrieve 10 contexts
            batch_size=5,       # Process 5 at a time
        )

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print()
        print("=" * 70)
        print("📊 RAGAS EVALUATION RESULTS")
        print("=" * 70)
        print()
        print(f"⏱️  Duration: {results.duration_seconds:.1f} seconds ({results.duration_seconds/60:.1f} minutes)")
        print(f"📈 Samples evaluated: {results.sample_count}")
        print(f"🗂️  Namespace: {results.namespace}")
        print()
        print("📉 Overall Metrics:")
        metrics = results.overall_metrics
        print(f"   • Context Precision: {metrics.context_precision*100:.1f}%")
        print(f"   • Context Recall:    {metrics.context_recall*100:.1f}%")
        print(f"   • Faithfulness:      {metrics.faithfulness*100:.1f}%")
        print(f"   • Answer Relevancy:  {metrics.answer_relevancy*100:.1f}%")
        print()

        # Per-intent breakdown
        if results.per_intent_metrics:
            print("📊 Per-Intent Breakdown:")
            for intent_metrics in results.per_intent_metrics:
                print(f"   [{intent_metrics.intent}] ({intent_metrics.sample_count} samples)")
                print(f"      CP: {intent_metrics.metrics.context_precision*100:.1f}% | "
                      f"CR: {intent_metrics.metrics.context_recall*100:.1f}% | "
                      f"F: {intent_metrics.metrics.faithfulness*100:.1f}% | "
                      f"AR: {intent_metrics.metrics.answer_relevancy*100:.1f}%")
            print()

        # Save results
        output_file = Path(__file__).parent.parent / f"data/evaluation/ragas_results_gpt120b_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Convert dataclass to dict for JSON serialization
        from dataclasses import asdict
        results_dict = asdict(results)
        with open(output_file, "w") as f:
            json.dump(results_dict, f, indent=2, default=str)
        print(f"💾 Results saved to: {output_file}")

    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
