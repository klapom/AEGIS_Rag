"""RAGAS evaluation on first 20 questions - Sprint 92 parallel testing."""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.ragas_evaluator import RAGASEvaluator, BenchmarkSample


async def main():
    print("=" * 60)
    print("🔬 RAGAS Evaluation - First 20 Questions (Sprint 92)")
    print("=" * 60)
    print()

    # Load questions
    questions_file = Path(__file__).parent.parent / "data/evaluation/ragas_phase1_questions.jsonl"

    if not questions_file.exists():
        print(f"❌ Questions file not found: {questions_file}")
        return

    # Load first 20 questions
    questions = []
    with open(questions_file, "r") as f:
        for i, line in enumerate(f):
            if i >= 20:
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
        print(f"   {i+1}. {s.question[:60]}...")
    print(f"   ... and {len(samples) - 3} more")
    print()

    # Initialize evaluator
    print("🔧 Initializing RAGAS Evaluator...")
    evaluator = RAGASEvaluator(
        namespace="ragas_phase1",  # Use phase1 namespace
        llm_model="Nemotron3",     # Use Nemotron3 for evaluation
        embedding_model="bge-m3:latest",
    )
    print(f"   ✅ Namespace: {evaluator.namespace}")
    print(f"   ✅ LLM: {evaluator.llm_model}")
    print()

    # Run evaluation
    print(f"🚀 Starting RAGAS evaluation on {len(samples)} samples...")
    print(f"   Started at: {datetime.now().strftime('%H:%M:%S')}")
    print()

    start_time = datetime.now()

    try:
        results = await evaluator.evaluate_rag_pipeline(
            dataset=samples,
            sample_size=len(samples),
            top_k=10,  # Retrieve top 10 contexts
        )

        duration = (datetime.now() - start_time).total_seconds()

        print()
        print("=" * 60)
        print("📊 RAGAS RESULTS")
        print("=" * 60)
        print()
        print(f"   Context Precision:  {results.overall_metrics.context_precision:.3f}")
        print(f"   Context Recall:     {results.overall_metrics.context_recall:.3f}")
        print(f"   Faithfulness:       {results.overall_metrics.faithfulness:.3f}")
        print(f"   Answer Relevancy:   {results.overall_metrics.answer_relevancy:.3f}")
        print()
        print(f"   Duration:           {duration:.1f}s ({duration/len(samples):.1f}s per question)")
        print(f"   Samples evaluated:  {len(samples)}")
        print()

        # Save results
        results_file = Path(__file__).parent.parent / f"data/evaluation/results/ragas_eval_20_sprint92_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        results_file.parent.mkdir(parents=True, exist_ok=True)

        with open(results_file, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "sprint": "92",
                "samples_count": len(samples),
                "namespace": "ragas_phase1",
                "metrics": {
                    "context_precision": results.overall_metrics.context_precision,
                    "context_recall": results.overall_metrics.context_recall,
                    "faithfulness": results.overall_metrics.faithfulness,
                    "answer_relevancy": results.overall_metrics.answer_relevancy,
                },
                "duration_seconds": duration,
                "per_sample_results": [
                    {
                        "question": s.question,
                        "ground_truth": s.ground_truth,
                        "metadata": s.metadata,
                    }
                    for s in samples
                ]
            }, f, indent=2)

        print(f"💾 Results saved to: {results_file.name}")
        print()

    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
