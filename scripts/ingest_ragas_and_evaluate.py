#!/usr/bin/env python3
"""Ingest RAGAS documents via LangGraph pipeline and run evaluations.

Sprint 42: Unified chunk IDs test with multiple documents.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

import structlog

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langgraph.graph import END, StateGraph

from src.components.graph_rag.lightrag_wrapper import get_lightrag_wrapper_async
from src.components.ingestion.ingestion_state import IngestionState
from src.components.ingestion.langgraph_nodes import (
    chunking_node,
    embedding_node,
    graph_extraction_node,
)
from src.core.config import settings

logger = structlog.get_logger(__name__)


def create_post_parse_pipeline():
    """Create LangGraph pipeline starting AFTER parsing (chunking → embedding → graph)."""
    graph = StateGraph(IngestionState)

    graph.add_node("chunking", chunking_node)
    graph.add_node("embedding", embedding_node)
    graph.add_node("graph", graph_extraction_node)

    graph.set_entry_point("chunking")
    graph.add_edge("chunking", "embedding")
    graph.add_edge("embedding", "graph")
    graph.add_edge("graph", END)

    return graph.compile()


def create_state_from_ragas(question_data: dict, namespace_id: str = "ragas_eval") -> IngestionState:
    """Create IngestionState from RAGAS question data."""
    question_id = question_data["metadata"]["question_id"]
    contexts = question_data["contexts"]

    # Combine all contexts into a single text
    combined_text = "\n\n".join(contexts)

    # Generate document_id from question_id
    import hashlib
    document_id = hashlib.md5(question_id.encode()).hexdigest()[:16]

    return IngestionState(
        document_path=f"/virtual/ragas/{question_id}.txt",
        document_id=document_id,
        parsed_content=combined_text,
        docling_status="completed",
        namespace_id=namespace_id,
        metadata={
            "source": "ragas_hotpotqa",
            "question_id": question_id,
            "question": question_data["question"],
            "ground_truth": question_data["ground_truth"],
        },
        errors=[],
    )


async def ingest_documents(num_docs: int = 10):
    """Ingest N documents from RAGAS dataset via LangGraph pipeline."""
    logger.info("=" * 70)
    logger.info(f"INGESTING {num_docs} RAGAS DOCUMENTS VIA LANGGRAPH")
    logger.info("=" * 70)

    # Load RAGAS dataset
    dataset_path = Path("reports/track_a_evaluation/datasets/hotpotqa_eval.jsonl")

    if not dataset_path.exists():
        logger.error(f"Dataset not found: {dataset_path}")
        return []

    # Load first N questions
    questions = []
    with open(dataset_path) as f:
        for i, line in enumerate(f):
            if i >= num_docs:
                break
            questions.append(json.loads(line))

    logger.info(f"Loaded {len(questions)} questions from RAGAS dataset")

    # Create pipeline
    pipeline = create_post_parse_pipeline()

    # Ingest each document
    ingested = []
    total_start = time.time()

    for i, question in enumerate(questions):
        question_id = question["metadata"]["question_id"]
        logger.info(f"\n[{i+1}/{len(questions)}] Ingesting {question_id}...")

        try:
            # Create state
            state = create_state_from_ragas(question)

            # Run pipeline
            doc_start = time.time()
            final_state = await pipeline.ainvoke(state)
            doc_time = time.time() - doc_start

            # Check status
            if final_state.get("graph_status") == "completed":
                ingested.append({
                    "question_id": question_id,
                    "document_id": state["document_id"],
                    "question": question["question"],
                    "ground_truth": question["ground_truth"],
                    "time_seconds": doc_time,
                    "entities": final_state.get("total_entities_extracted", 0),
                    "relations": final_state.get("total_relations_created", 0),
                })
                logger.info(f"  ✓ Ingested in {doc_time:.1f}s")
            else:
                logger.warning(f"  ✗ Failed: {final_state.get('errors', [])}")

        except Exception as e:
            logger.error(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()

    total_time = time.time() - total_start
    logger.info(f"\nTotal ingestion time: {total_time:.1f}s")
    logger.info(f"Successfully ingested: {len(ingested)}/{len(questions)}")

    return ingested


async def run_evaluations(ingested_docs: list, num_evals: int = 5):
    """Run evaluations against ingested documents."""
    logger.info("\n" + "=" * 70)
    logger.info(f"RUNNING {num_evals} EVALUATIONS")
    logger.info("=" * 70)

    if len(ingested_docs) < num_evals:
        logger.warning(f"Only {len(ingested_docs)} docs available, adjusting eval count")
        num_evals = len(ingested_docs)

    # Import search components
    from src.components.vector_search.hybrid_search import HybridSearch
    from src.components.graph_rag.dual_level_search import DualLevelSearch
    from src.components.llm_proxy.aegis_llm_proxy import AegisLLMProxy
    from src.components.llm_proxy.models import LLMTask, TaskType

    # Initialize components
    hybrid_search = HybridSearch()
    graph_search = DualLevelSearch()
    llm_proxy = AegisLLMProxy()

    results = []

    for i, doc in enumerate(ingested_docs[:num_evals]):
        question = doc["question"]
        ground_truth = doc["ground_truth"]
        question_id = doc["question_id"]

        logger.info(f"\n[{i+1}/{num_evals}] Evaluating: {question_id}")
        logger.info(f"  Question: {question[:80]}...")
        logger.info(f"  Ground truth: {ground_truth}")

        try:
            # Hybrid vector search (Vector + BM25 + RRF)
            logger.info("  Running hybrid vector search...")
            vector_start = time.time()
            vector_results = await hybrid_search.hybrid_search(
                query=question,
                top_k=5,
            )
            vector_time = time.time() - vector_start

            # Graph search (returns GraphQueryResult)
            logger.info("  Running graph search...")
            graph_start = time.time()
            graph_result = await graph_search.hybrid_search(
                query=question,
                top_k=5,
            )
            graph_time = time.time() - graph_start

            # Combine contexts
            contexts = []
            # vector_results is dict with "results" key containing list
            for r in vector_results.get("results", [])[:3]:
                contexts.append(r.get("content", r.get("text", "")))

            # Add graph context (GraphQueryResult has .context, .entities, .answer)
            if graph_result.context:
                contexts.append(graph_result.context[:1000])
            for entity in graph_result.entities[:2]:
                if entity.description:
                    contexts.append(f"{entity.name}: {entity.description}")

            combined_context = "\n\n".join(contexts)

            # Generate answer via LLM
            logger.info("  Generating answer...")
            llm_start = time.time()

            prompt_text = f"""Based on the following context, answer the question concisely.

Context:
{combined_context[:3000]}

Question: {question}

Answer (be concise, 1-2 sentences):"""

            task = LLMTask(
                task_type=TaskType.GENERATION,
                prompt=prompt_text,
            )
            response = await llm_proxy.generate(task)

            answer = response.content.strip() if response.content else ""
            llm_time = time.time() - llm_start

            # Simple evaluation: check if ground truth appears in answer
            is_correct = ground_truth.lower() in answer.lower()

            result = {
                "question_id": question_id,
                "question": question,
                "ground_truth": ground_truth,
                "answer": answer,
                "is_correct": is_correct,
                "vector_results": len(vector_results.get("results", [])),
                "graph_entities": len(graph_result.entities),
                "graph_relationships": len(graph_result.relationships),
                "vector_time": vector_time,
                "graph_time": graph_time,
                "llm_time": llm_time,
            }

            results.append(result)

            logger.info(f"  Answer: {answer[:100]}...")
            logger.info(f"  Correct: {'✓' if is_correct else '✗'}")
            logger.info(f"  Times: vector={vector_time:.2f}s, graph={graph_time:.2f}s, llm={llm_time:.2f}s")

        except Exception as e:
            logger.error(f"  Error: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("EVALUATION SUMMARY")
    logger.info("=" * 70)

    correct = sum(1 for r in results if r.get("is_correct"))
    logger.info(f"Correct answers: {correct}/{len(results)} ({100*correct/len(results):.1f}%)")

    avg_vector = sum(r["vector_time"] for r in results) / len(results) if results else 0
    avg_graph = sum(r["graph_time"] for r in results) / len(results) if results else 0
    avg_llm = sum(r["llm_time"] for r in results) / len(results) if results else 0

    logger.info(f"Avg vector search: {avg_vector:.2f}s")
    logger.info(f"Avg graph search:  {avg_graph:.2f}s")
    logger.info(f"Avg LLM generation: {avg_llm:.2f}s")

    return results


async def main():
    """Main entry point."""
    # Check GPU status first
    logger.info("Checking Ollama GPU status...")
    import subprocess
    result = subprocess.run(
        ["docker", "exec", "aegis-ollama", "nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader"],
        capture_output=True,
        text=True,
    )
    logger.info(f"GPU utilization: {result.stdout.strip()}")

    # Ingest documents
    ingested = await ingest_documents(num_docs=10)

    if not ingested:
        logger.error("No documents ingested, aborting evaluations")
        return

    # Run evaluations
    await run_evaluations(ingested, num_evals=5)


if __name__ == "__main__":
    asyncio.run(main())
