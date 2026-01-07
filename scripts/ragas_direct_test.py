"""Direct RAGAS test without pytest - Sprint 75 debugging."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.ragas_evaluator import RAGASEvaluator, BenchmarkSample


async def main():
    print("🔧 Initializing RAGAS Evaluator...")

    evaluator = RAGASEvaluator(
        namespace="default",  # Using default namespace with 129 docs
        llm_model="qwen2.5:7b",  # Sprint 75: qwen2.5 for RAGAS (JSON-compatible)
        embedding_model="bge-m3:latest",  # Ignored, uses native service
    )

    print("✅ Evaluator initialized")
    print(f"   Namespace: {evaluator.namespace}")
    print(f"   LLM: {evaluator.llm_model}")
    print("")

    # Create minimal test dataset (1 sample)
    test_samples = [
        BenchmarkSample(
            question="What is BGE-M3?",
            ground_truth="BGE-M3 is a 1024-dimensional multilingual embedding model used in AEGIS RAG.",
            contexts=[],  # Will be retrieved
            answer="",    # Will be generated
            metadata={"intent": "factual", "domain": "embeddings", "difficulty": "easy"}
        )
    ]

    print(f"📊 Running RAGAS evaluation on {len(test_samples)} sample(s)...")
    print("")

    try:
        results = await evaluator.evaluate_rag_pipeline(
            dataset=test_samples,
            sample_size=1,
            top_k=5,
        )

        print("✅ Evaluation completed!")
        print("")
        print("📈 Results:")
        print(f"   Context Precision: {results.overall_metrics.context_precision:.3f}")
        print(f"   Context Recall: {results.overall_metrics.context_recall:.3f}")
        print(f"   Faithfulness: {results.overall_metrics.faithfulness:.3f}")
        print(f"   Answer Relevancy: {results.overall_metrics.answer_relevancy:.3f}")
        print(f"   Duration: {results.duration_seconds:.1f}s")

    except Exception as e:
        print(f"❌ Evaluation failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
