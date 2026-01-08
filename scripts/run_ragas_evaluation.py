#!/usr/bin/env python3
"""RAGAS Evaluation Runner for AegisRAG System.

Sprint 79 Feature 79.8: RAGAS 0.4.2 Upgrade with Experiment API.

This script:
1. Loads RAGAS dataset (questions, ground_truth, contexts)
2. Queries AegisRAG API with different retrieval modes
3. Collects answers + retrieved contexts
4. Computes RAGAS metrics (Context Precision, Recall, Faithfulness, Answer Relevancy)
5. Saves results for comparison

RAGAS 0.4.2 Changes:
- New @experiment() decorator API (replaces evaluate())
- llm_factory() requires OpenAI client
- Metrics from ragas.metrics.collections

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
from openai import AsyncOpenAI  # For Ollama OpenAI-compatible API (async needed for RAGAS)
from pydantic import BaseModel, Field
from ragas.embeddings import OpenAIEmbeddings  # RAGAS 0.4.2 modern embeddings
from ragas.llms import llm_factory  # RAGAS 0.4 unified LLM factory
from ragas.metrics.collections import (  # RAGAS 0.4.2 Collections metrics
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import settings


def get_ragas_llm():
    """Get LLM for RAGAS metrics (Faithfulness, Answer Relevancy).

    Uses gpt-oss:20b via Ollama for reliable evaluation.
    Better reasoning capabilities than Nemotron for complex metric computation.

    RAGAS 0.4.2: Collections metrics REQUIRE InstructorLLM via llm_factory().
    We use Ollama's OpenAI-compatible API (/v1 endpoint) to enable llm_factory().
    """
    # Create AsyncOpenAI client pointing to Ollama's OpenAI-compatible endpoint
    ollama_openai_client = AsyncOpenAI(
        base_url=f"{settings.ollama_base_url}/v1",
        api_key="ollama",  # Dummy key (Ollama doesn't require auth)
    )

    # Use llm_factory with Ollama via OpenAI-compatible API
    return llm_factory(
        model="gpt-oss:20b",
        client=ollama_openai_client,
        temperature=0.0,  # Deterministic for evaluation
    )


def get_ollama_openai_client():
    """Get AsyncOpenAI client pointing to Ollama's OpenAI-compatible endpoint.

    RAGAS 0.4.2 requires an AsyncOpenAI client for ascore() metrics.
    Ollama provides an OpenAI-compatible API at /v1 endpoint.
    """
    return AsyncOpenAI(
        base_url=f"{settings.ollama_base_url}/v1",
        api_key="ollama",  # Dummy key (Ollama doesn't require auth)
    )


def get_ragas_embeddings(ollama_client: AsyncOpenAI):
    """Get embeddings for RAGAS metrics.

    RAGAS 0.4.2: Use OpenAIEmbeddings with Ollama client.
    """
    return OpenAIEmbeddings(
        model="bge-m3",  # Ollama BGE-M3 model
        client=ollama_client,
    )


logger = structlog.get_logger(__name__)


# RAGAS 0.4.2: Define result model for experiment
class RAGASMetricsResult(BaseModel):
    """RAGAS evaluation metrics result."""
    context_precision: float = Field(description="Context precision score (0-1)")
    context_recall: float = Field(description="Context recall score (0-1)")
    faithfulness: float = Field(description="Faithfulness score (0-1)")
    answer_relevancy: float = Field(description="Answer relevancy score (0-1)")


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


async def compute_ragas_metrics_for_sample(
    question: str,
    answer: str,
    contexts: list[str],
    ground_truth: str,
    ragas_llm: Any,
    ragas_embeddings: Any,
) -> RAGASMetricsResult:
    """Compute RAGAS metrics for a single sample.

    RAGAS 0.4.2: Use async metric scoring with ascore().

    Args:
        question: User question
        answer: Generated answer
        contexts: Retrieved contexts
        ground_truth: Ground truth answer
        ragas_llm: LLM instance from llm_factory()
        ragas_embeddings: Embeddings from OpenAIEmbeddings (async)

    Returns:
        RAGASMetricsResult with all 4 metric scores
    """
    # Initialize metrics (RAGAS 0.4.2 Collections API)
    context_precision = ContextPrecision(llm=ragas_llm, embeddings=ragas_embeddings)
    context_recall = ContextRecall(llm=ragas_llm, embeddings=ragas_embeddings)
    faithfulness = Faithfulness(llm=ragas_llm)
    answer_relevancy = AnswerRelevancy(llm=ragas_llm, embeddings=ragas_embeddings)

    # Compute metrics (RAGAS 0.4.2: use ascore() method with correct signatures)
    try:
        # Context Precision: uses reference (ground truth)
        cp_result = await context_precision.ascore(
            user_input=question,
            reference=ground_truth,
            retrieved_contexts=contexts,
        )

        # Context Recall: uses reference (ground truth)
        cr_result = await context_recall.ascore(
            user_input=question,
            retrieved_contexts=contexts,
            reference=ground_truth,
        )

        # Faithfulness: uses response (generated answer)
        f_result = await faithfulness.ascore(
            user_input=question,
            response=answer,
            retrieved_contexts=contexts,
        )

        # Answer Relevancy: uses only response (no contexts!)
        ar_result = await answer_relevancy.ascore(
            user_input=question,
            response=answer,
        )

        return RAGASMetricsResult(
            context_precision=cp_result.value if hasattr(cp_result, 'value') else float(cp_result),
            context_recall=cr_result.value if hasattr(cr_result, 'value') else float(cr_result),
            faithfulness=f_result.value if hasattr(f_result, 'value') else float(f_result),
            answer_relevancy=ar_result.value if hasattr(ar_result, 'value') else float(ar_result),
        )
    except Exception as e:
        logger.error(f"Metric computation failed: {e}")
        # Return zeros on failure
        return RAGASMetricsResult(
            context_precision=0.0,
            context_recall=0.0,
            faithfulness=0.0,
            answer_relevancy=0.0,
        )


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
    logger.info(f"RAGAS EVALUATION - Sprint 79 Feature 79.8 (RAGAS 0.4.2)")
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

    total_query_time = time.time() - start_time

    # Compute RAGAS metrics
    logger.info("\n" + "=" * 80)
    logger.info("COMPUTING RAGAS METRICS (0.4.2 API)")
    logger.info("=" * 80)
    logger.info("Using GPT-OSS:20b (Ollama) for LLM-based metrics...")

    # Get LLM and embeddings for RAGAS (RAGAS 0.4.2)
    ragas_llm = get_ragas_llm()
    ollama_client = get_ollama_openai_client()
    ragas_embeddings = get_ragas_embeddings(ollama_client)

    # Track metrics per sample
    all_metrics = []
    metrics_start_time = time.time()

    try:
        # RAGAS 0.4.2: Compute metrics for each sample individually
        for i, result in enumerate(results):
            logger.info(f"\nComputing metrics for sample {i+1}/{len(results)}...")

            sample_start = time.time()
            sample_metrics = await compute_ragas_metrics_for_sample(
                question=result["question"],
                answer=result["answer"],
                contexts=result["contexts"],
                ground_truth=result["ground_truth"],
                ragas_llm=ragas_llm,
                ragas_embeddings=ragas_embeddings,
            )
            sample_time = time.time() - sample_start

            all_metrics.append(sample_metrics)
            result["metrics"] = sample_metrics.model_dump()
            result["metrics_time"] = sample_time

            logger.info(f"  ✓ Metrics computed in {sample_time:.2f}s")
            logger.info(f"    CP: {sample_metrics.context_precision:.3f}, "
                       f"CR: {sample_metrics.context_recall:.3f}, "
                       f"F: {sample_metrics.faithfulness:.3f}, "
                       f"AR: {sample_metrics.answer_relevancy:.3f}")

        metrics_total_time = time.time() - metrics_start_time

        # Compute average metrics
        avg_metrics = {
            "context_precision": sum(m.context_precision for m in all_metrics) / len(all_metrics),
            "context_recall": sum(m.context_recall for m in all_metrics) / len(all_metrics),
            "faithfulness": sum(m.faithfulness for m in all_metrics) / len(all_metrics),
            "answer_relevancy": sum(m.answer_relevancy for m in all_metrics) / len(all_metrics),
            "per_sample_scores": {
                "context_precision": [m.context_precision for m in all_metrics],
                "context_recall": [m.context_recall for m in all_metrics],
                "faithfulness": [m.faithfulness for m in all_metrics],
                "answer_relevancy": [m.answer_relevancy for m in all_metrics],
            },
            "total_time_seconds": metrics_total_time,
            "avg_time_per_sample": metrics_total_time / len(all_metrics),
        }

        logger.info("\n" + "=" * 80)
        logger.info("RAGAS METRICS (AVERAGED)")
        logger.info("=" * 80)
        logger.info(f"Context Precision: {avg_metrics['context_precision']:.4f}")
        logger.info(f"Context Recall:    {avg_metrics['context_recall']:.4f}")
        logger.info(f"Faithfulness:      {avg_metrics['faithfulness']:.4f}")
        logger.info(f"Answer Relevancy:  {avg_metrics['answer_relevancy']:.4f}")
        logger.info(f"\nMetrics Timing:")
        logger.info(f"  Total: {metrics_total_time:.1f}s")
        logger.info(f"  Avg per sample: {avg_metrics['avg_time_per_sample']:.1f}s")

        metrics = avg_metrics

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
            "total_query_time_seconds": total_query_time,
            "total_metrics_time_seconds": metrics.get("total_time_seconds", 0),
            "total_time_seconds": total_query_time + metrics.get("total_time_seconds", 0),
            "timestamp": timestamp,
            "ragas_version": "0.4.2",
        },
        "metrics": metrics,
        "per_question_results": results,
    }

    with open(results_file, "w") as f:
        json.dump(output_data, f, indent=2)

    logger.info(f"\n✓ Results saved to: {results_file}")

    # Summary
    total_time = total_query_time + metrics.get("total_time_seconds", 0)

    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    logger.info(f"RAGAS Version: 0.4.2")
    logger.info(f"Mode: {mode}")
    logger.info(f"Questions evaluated: {len(questions_data)}")
    logger.info(f"Query time: {total_query_time:.1f}s")
    logger.info(f"Metrics time: {metrics.get('total_time_seconds', 0):.1f}s")
    logger.info(f"Total time: {total_time:.1f}s")
    logger.info(f"Avg time per question (query only): {total_query_time/len(questions_data):.2f}s")
    logger.info(f"Avg time per sample (metrics): {metrics.get('avg_time_per_sample', 0):.2f}s")
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
