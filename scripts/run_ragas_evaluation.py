#!/usr/bin/env python3
"""RAGAS Evaluation Runner for AegisRAG System.

Sprint 76 Feature 76.3: End-to-end RAGAS evaluation with all 4 metrics.

This script:
1. Loads RAGAS dataset (questions, ground_truth, contexts)
2. Queries AegisRAG API with different retrieval modes
3. Collects answers + retrieved contexts
4. Computes RAGAS metrics (Context Precision, Recall, Faithfulness, Answer Relevancy)
5. Saves results for comparison

Usage:
    poetry run python scripts/run_ragas_evaluation.py --namespace ragas_eval --mode hybrid
    poetry run python scripts/run_ragas_evaluation.py --namespace ragas_eval --mode vector
    poetry run python scripts/run_ragas_evaluation.py --namespace ragas_eval --mode graph
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any

import httpx
import structlog
from datasets import Dataset
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import HuggingFaceEmbeddings
from ragas import evaluate
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)
from ragas.run_config import RunConfig

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import settings


def get_ragas_llm():
    """Get LLM for RAGAS metrics (Faithfulness, Answer Relevancy).

    Uses gpt-oss:20b via Ollama for reliable evaluation.
    Better reasoning capabilities than Nemotron for complex metric computation.
    """
    return ChatOllama(
        model="gpt-oss:20b",
        base_url=settings.ollama_base_url,
        temperature=0.0,  # Deterministic for evaluation
    )


def get_ragas_embeddings():
    """Get embeddings for RAGAS metrics.

    Uses BGE-M3 via HuggingFace/sentence-transformers on GPU.
    Same model as production system for consistency.
    GPU provides ~10-80x speedup for embedding generation.
    """
    return HuggingFaceEmbeddings(
        model_name="BAAI/bge-m3",
        model_kwargs={
            "device": "cuda",
            "trust_remote_code": True,
        },
        encode_kwargs={
            "normalize_embeddings": True,
            "batch_size": 32,  # Smaller batch to avoid OOM with gpt-oss:20b
        },
    )

logger = structlog.get_logger(__name__)


async def query_aegis_rag(
    question: str,
    namespace_id: str = "ragas_eval",
    mode: str = "hybrid",
) -> dict[str, Any]:
    """Query AegisRAG API and return answer + contexts.

    Args:
        question: User question
        namespace_id: Namespace for retrieval filtering
        mode: Retrieval mode (vector, hybrid, graph)

    Returns:
        Dict with answer, contexts, sources, mode
    """
    api_base = "http://localhost:8000"

    async with httpx.AsyncClient(timeout=180.0, follow_redirects=True) as client:
        # Call chat endpoint
        response = await client.post(
            f"{api_base}/api/v1/chat/",
            json={
                "query": question,
                "namespaces": [namespace_id],
                "intent": mode,  # vector, hybrid, graph
                "session_id": "ragas_eval_session",
                "include_sources": True,
            },
        )

        if response.status_code != 200:
            logger.error(
                "api_request_failed",
                status=response.status_code,
                error=response.text,
            )
            raise Exception(f"API request failed: {response.status_code}")

        data = response.json()

        # Extract answer and contexts
        answer = data.get("answer", "")
        sources = data.get("sources", [])

        # Extract context texts from sources
        contexts = [source.get("text", "") for source in sources if source.get("text")]

        return {
            "answer": answer,
            "contexts": contexts,
            "sources": sources,
            "mode": mode,
            "question": question,
        }


async def run_ragas_evaluation(
    dataset_path: str = "data/evaluation/ragas_dataset.jsonl",
    namespace_id: str = "ragas_eval",
    mode: str = "hybrid",
    max_questions: int = -1,
    output_dir: str = "data/evaluation/results",
) -> dict[str, Any]:
    """Run RAGAS evaluation on AegisRAG system.

    Args:
        dataset_path: Path to RAGAS JSONL dataset
        namespace_id: Namespace for retrieval filtering
        mode: Retrieval mode (vector, hybrid, graph)
        max_questions: Max questions to evaluate (-1 = all)
        output_dir: Directory to save results

    Returns:
        Evaluation results with all 4 RAGAS metrics
    """
    logger.info("=" * 80)
    logger.info(f"RAGAS EVALUATION - Sprint 76 Feature 76.3")
    logger.info("=" * 80)
    logger.info(f"Dataset: {dataset_path}")
    logger.info(f"Namespace: {namespace_id}")
    logger.info(f"Mode: {mode}")

    # Load dataset
    dataset_file = Path(dataset_path)
    if not dataset_file.exists():
        raise FileNotFoundError(f"Dataset not found: {dataset_path}")

    questions_data = []
    with open(dataset_file) as f:
        for i, line in enumerate(f):
            if max_questions > 0 and i >= max_questions:
                break
            questions_data.append(json.loads(line))

    logger.info(f"Loaded {len(questions_data)} questions")

    # Query AegisRAG for each question
    logger.info("\n" + "=" * 80)
    logger.info("QUERYING AEGIS RAG SYSTEM")
    logger.info("=" * 80)

    results = []
    start_time = time.time()

    for i, q_data in enumerate(questions_data):
        question = q_data["question"]
        ground_truth = q_data["ground_truth"]
        expected_contexts = q_data["contexts"]

        logger.info(f"\n[{i+1}/{len(questions_data)}] {question[:80]}...")

        try:
            # Query system
            query_start = time.time()
            response = await query_aegis_rag(
                question=question,
                namespace_id=namespace_id,
                mode=mode,
            )
            query_time = time.time() - query_start

            # Collect for RAGAS evaluation
            result = {
                "question": question,
                "answer": response["answer"],
                "contexts": response["contexts"],
                "ground_truth": ground_truth,
                "expected_contexts": expected_contexts,
                "mode": mode,
                "query_time": query_time,
                "num_contexts_retrieved": len(response["contexts"]),
            }
            results.append(result)

            logger.info(f"  ✓ Answer: {response['answer'][:100]}...")
            logger.info(f"  Retrieved {len(response['contexts'])} contexts in {query_time:.2f}s")

        except Exception as e:
            logger.error(f"  ✗ Query failed: {e}")
            # Add failed result with empty answer
            results.append({
                "question": question,
                "answer": "",
                "contexts": [],
                "ground_truth": ground_truth,
                "expected_contexts": expected_contexts,
                "mode": mode,
                "query_time": 0,
                "num_contexts_retrieved": 0,
                "error": str(e),
            })

    total_time = time.time() - start_time

    # Prepare RAGAS dataset
    logger.info("\n" + "=" * 80)
    logger.info("COMPUTING RAGAS METRICS")
    logger.info("=" * 80)

    # Convert to RAGAS dataset format
    ragas_data = {
        "question": [r["question"] for r in results],
        "answer": [r["answer"] for r in results],
        "contexts": [r["contexts"] for r in results],
        "ground_truth": [r["ground_truth"] for r in results],
    }

    dataset = Dataset.from_dict(ragas_data)

    # Compute RAGAS metrics
    logger.info("Computing metrics (this may take a few minutes)...")
    logger.info("Using GPT-OSS:20b (Ollama) for LLM-based metrics...")

    # Get LLM and embeddings for RAGAS
    ragas_llm = get_ragas_llm()
    ragas_embeddings = get_ragas_embeddings()

    try:
        # RAGAS 0.3.9 API with custom LLM/embeddings
        # Sprint 78: Use 1 worker for fully sequential execution to prevent timeouts with GPT-OSS:20b
        run_config = RunConfig(
            max_workers=1,  # Sequential execution to prevent GPU contention with slow GPT-OSS:20b
            timeout=300,  # 300s timeout per job (GPT-OSS:20b needs ~17s per query)
            max_retries=3,  # Reduce retries to fail faster
        )

        evaluation_result = evaluate(
            dataset,
            metrics=[
                context_precision,
                context_recall,
                faithfulness,
                answer_relevancy,
            ],
            llm=ragas_llm,
            embeddings=ragas_embeddings,
            run_config=run_config,
        )

        # RAGAS returns per-sample scores as lists - compute averages
        def safe_mean(values):
            """Compute mean, handling lists and NaN values."""
            if isinstance(values, list):
                valid_values = [v for v in values if v is not None and not (isinstance(v, float) and v != v)]  # Filter None and NaN
                return sum(valid_values) / len(valid_values) if valid_values else 0.0
            return float(values) if values is not None else 0.0

        metrics = {
            "context_precision": safe_mean(evaluation_result["context_precision"]),
            "context_recall": safe_mean(evaluation_result["context_recall"]),
            "faithfulness": safe_mean(evaluation_result["faithfulness"]),
            "answer_relevancy": safe_mean(evaluation_result["answer_relevancy"]),
            "per_sample_scores": {
                "context_precision": evaluation_result["context_precision"],
                "context_recall": evaluation_result["context_recall"],
                "faithfulness": evaluation_result["faithfulness"],
                "answer_relevancy": evaluation_result["answer_relevancy"],
            }
        }

        logger.info("\n" + "=" * 80)
        logger.info("RAGAS METRICS")
        logger.info("=" * 80)
        logger.info(f"Context Precision: {metrics['context_precision']:.4f}")
        logger.info(f"Context Recall:    {metrics['context_recall']:.4f}")
        logger.info(f"Faithfulness:      {metrics['faithfulness']:.4f}")
        logger.info(f"Answer Relevancy:  {metrics['answer_relevancy']:.4f}")

    except Exception as e:
        logger.error(f"RAGAS evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        metrics = {
            "context_precision": 0.0,
            "context_recall": 0.0,
            "faithfulness": 0.0,
            "answer_relevancy": 0.0,
            "error": str(e),
        }

    # Save results
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    results_file = output_path / f"ragas_eval_{mode}_{timestamp}.json"

    output_data = {
        "metadata": {
            "mode": mode,
            "namespace_id": namespace_id,
            "dataset_path": dataset_path,
            "num_questions": len(questions_data),
            "total_time_seconds": total_time,
            "timestamp": timestamp,
        },
        "metrics": metrics,
        "per_question_results": results,
    }

    with open(results_file, "w") as f:
        json.dump(output_data, f, indent=2)

    logger.info(f"\n✓ Results saved to: {results_file}")

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Mode: {mode}")
    logger.info(f"Questions evaluated: {len(questions_data)}")
    logger.info(f"Total time: {total_time:.1f}s")
    logger.info(f"Avg time per question: {total_time/len(questions_data):.2f}s")
    logger.info(f"\nMetrics:")
    logger.info(f"  Context Precision: {metrics['context_precision']:.4f}")
    logger.info(f"  Context Recall:    {metrics['context_recall']:.4f}")
    logger.info(f"  Faithfulness:      {metrics['faithfulness']:.4f}")
    logger.info(f"  Answer Relevancy:  {metrics['answer_relevancy']:.4f}")

    return output_data


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run RAGAS evaluation on AegisRAG")
    parser.add_argument(
        "--namespace",
        default="ragas_eval",
        help="Namespace ID for retrieval filtering (default: ragas_eval)",
    )
    parser.add_argument(
        "--mode",
        default="hybrid",
        choices=["vector", "hybrid", "graph"],
        help="Retrieval mode (default: hybrid)",
    )
    parser.add_argument(
        "--max-questions",
        type=int,
        default=-1,
        help="Maximum questions to evaluate (-1 = all)",
    )
    parser.add_argument(
        "--dataset",
        default="data/evaluation/ragas_dataset.jsonl",
        help="Path to RAGAS dataset (default: data/evaluation/ragas_dataset.jsonl)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/evaluation/results",
        help="Output directory for results (default: data/evaluation/results)",
    )

    args = parser.parse_args()

    # Run evaluation
    await run_ragas_evaluation(
        dataset_path=args.dataset,
        namespace_id=args.namespace,
        mode=args.mode,
        max_questions=args.max_questions,
        output_dir=args.output_dir,
    )


if __name__ == "__main__":
    asyncio.run(main())
