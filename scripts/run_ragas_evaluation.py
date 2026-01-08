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
from ragas.embeddings.base import BaseRagasEmbeddings, BaseRagasEmbedding, embedding_factory  # RAGAS 0.4.2 base + factory
from ragas.llms import llm_factory  # RAGAS 0.4 unified LLM factory
from sentence_transformers import SentenceTransformer  # For BGE-M3 embeddings
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
    # CRITICAL FIX (Sprint 79.8): Increase max_tokens to handle RAGAS Few-Shot prompts
    # RAGAS prompts are ~6000 tokens, default 3072 was causing timeouts
    return llm_factory(
        model="gpt-oss:20b",
        client=ollama_openai_client,
        temperature=0.0,  # Deterministic for evaluation
        max_tokens=16384,  # Increased from default 3072 to handle complex prompts
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


class OllamaEmbeddings(BaseRagasEmbeddings):
    """Ollama embeddings wrapper for RAGAS 0.4.2.

    Sprint 79.8.1: Use Ollama's native embedding API (nomic-embed-text).
    This is faster and more aligned with our Ollama-based architecture.
    """

    def __init__(self, model: str = "nomic-embed-text", base_url: str = "http://localhost:11434"):
        """Initialize Ollama embeddings.

        Args:
            model: Ollama embedding model name (default: nomic-embed-text)
            base_url: Ollama API base URL
        """
        self.model = model
        self.base_url = base_url

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed documents asynchronously via Ollama API."""
        embeddings = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            for text in texts:
                response = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                )
                response.raise_for_status()
                data = response.json()
                embeddings.append(data["embedding"])
        return embeddings

    async def aembed_query(self, text: str) -> list[float]:
        """Embed query asynchronously via Ollama API."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed documents synchronously (fallback - not used by RAGAS 0.4.2)."""
        import requests
        embeddings = []
        for text in texts:
            response = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=60.0,
            )
            response.raise_for_status()
            embeddings.append(response.json()["embedding"])
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        """Embed query synchronously (fallback - not used by RAGAS 0.4.2)."""
        import requests
        response = requests.post(
            f"{self.base_url}/api/embeddings",
            json={"model": self.model, "prompt": text},
            timeout=60.0,
        )
        response.raise_for_status()
        return response.json()["embedding"]


class SimpleBGEM3Embeddings(BaseRagasEmbeddings):
    """Simple wrapper for BGE-M3 embeddings compatible with RAGAS 0.4.2.

    NOTE: This is kept for reference but OllamaEmbeddings is now preferred.
    """

    def __init__(self):
        """Initialize BGE-M3 model."""
        self.model = SentenceTransformer("BAAI/bge-m3")

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed documents asynchronously."""
        # SentenceTransformer is sync, but we can run in executor for async compat
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    async def aembed_query(self, text: str) -> list[float]:
        """Embed query asynchronously."""
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed documents synchronously (fallback)."""
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        """Embed query synchronously (fallback)."""
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()


class ModernBGEM3Embeddings(BaseRagasEmbedding):
    """Modern BGE-M3 embeddings for RAGAS 0.4.2 Collections metrics.

    Sprint 79.8.4: RAGAS 0.4.2 Collections metrics require BaseRagasEmbedding (singular)
    with embed_text() method, not BaseRagasEmbeddings (plural) with embed_documents().

    This is the "modern" interface that passes _validate_embeddings() checks.
    """

    def __init__(self):
        """Initialize BGE-M3 model."""
        self.model = SentenceTransformer("BAAI/bge-m3")

    def embed_text(self, text: str, **kwargs) -> list[float]:
        """Embed single text (modern interface, sync).

        RAGAS 0.4.2 Collections metrics call this method.
        """
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()

    async def aembed_text(self, text: str, **kwargs) -> list[float]:
        """Embed single text (modern interface, async).

        RAGAS 0.4.2 Collections metrics call this method.
        """
        # SentenceTransformer is sync, but wrap for async compatibility
        import asyncio
        return await asyncio.to_thread(self.embed_text, text, **kwargs)

    def embed_texts(self, texts: list[str], **kwargs) -> list[list[float]]:
        """Embed multiple texts (modern interface, sync, batch).

        Optional batch method - RAGAS provides default implementation.
        """
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    async def aembed_texts(self, texts: list[str], **kwargs) -> list[list[float]]:
        """Embed multiple texts (modern interface, async, batch).

        Optional batch method - RAGAS provides default implementation.
        """
        import asyncio
        return await asyncio.to_thread(self.embed_texts, texts, **kwargs)


def get_ragas_embeddings():
    """Get embeddings for RAGAS metrics.

    Sprint 79.8.1: Use RAGAS embedding_factory with Ollama's OpenAI-compatible endpoint.
    This creates "modern" embeddings that work with RAGAS 0.4.2 Collections metrics.

    Sprint 79.8.2: Fixed to use BGE-M3 (1024-dim) instead of nomic-embed-text (768-dim)
    to match ingestion embeddings (ADR-024).

    Sprint 79.8.3: Switched to SimpleBGEM3Embeddings (SentenceTransformer) due to Ollama
    NaN-bug with long texts. Direct SentenceTransformer is more robust and matches ingestion.

    Sprint 79.8.4: Switched to ModernBGEM3Embeddings (BaseRagasEmbedding) to pass
    Collections metrics _validate_embeddings() check. Requires embed_text() interface.
    """
    # Use ModernBGEM3Embeddings (SentenceTransformer BAAI/bge-m3 with modern interface)
    # This is the SAME model used in ingestion (ADR-024) - guaranteed 1024-dim
    # Implements BaseRagasEmbedding (singular) with embed_text() for Collections metrics
    return ModernBGEM3Embeddings()


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

    # Sprint 79.8.1: Increased timeout to 300s for complex graph queries
    async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
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

        # RAG Tuning: Extract detailed source metadata for analysis
        source_metadata = []
        for idx, source in enumerate(sources):
            meta = {
                "index": idx,
                "chunk_id": source.get("chunk_id", source.get("id", f"unknown_{idx}")),
                "document_id": source.get("document_id", "unknown"),
                "filename": source.get("filename", source.get("document_name", "unknown")),
                "section_title": source.get("section_title", source.get("title", "")),
                "text": source.get("text", ""),
                "text_length": len(source.get("text", "")),
                "score": source.get("score", source.get("similarity", None)),
                "retrieval_type": source.get("retrieval_type", mode),
            }
            source_metadata.append(meta)

        return {
            "answer": answer,
            "contexts": contexts,
            "sources": sources,
            "source_metadata": source_metadata,  # RAG Tuning: Detailed metadata
            "mode": mode,
            "question": question,
            "raw_response": data,  # RAG Tuning: Full API response for debugging
        }


async def compute_single_metric(
    metric_name: str,
    metric_func,
    metric_kwargs: dict,
    timeout: float,
) -> tuple[float, str, float, dict]:
    """Compute a single RAGAS metric with detailed logging.

    Args:
        metric_name: Name of the metric (for logging)
        metric_func: Async scoring function (metric.ascore)
        metric_kwargs: Keyword arguments for the metric
        timeout: Timeout in seconds

    Returns:
        Tuple of (score, status_message, time_taken, details_dict)
        details_dict contains RAG tuning data: reason, statements, verdicts, claims
    """
    start_time = time.time()
    details = {}  # RAG Tuning: Capture all available details

    try:
        result = await asyncio.wait_for(
            metric_func(**metric_kwargs),
            timeout=timeout,
        )
        elapsed = time.time() - start_time

        # Extract score value
        if hasattr(result, 'value'):
            score = float(result.value)
        else:
            score = float(result)

        # Log detailed result info
        status = "OK"
        logger.info(f"    [{metric_name}] ✓ Score: {score:.3f} in {elapsed:.1f}s")

        # RAG Tuning: Extract all available details from RAGAS result
        if hasattr(result, 'reason') and result.reason:
            details["reason"] = str(result.reason)
            reason_preview = str(result.reason)[:200]
            logger.info(f"    [{metric_name}] LLM Reason: {reason_preview}...")

        if hasattr(result, 'statements') and result.statements:
            details["statements"] = result.statements
            logger.info(f"    [{metric_name}] Statements analyzed: {len(result.statements)}")

        if hasattr(result, 'verdicts') and result.verdicts:
            details["verdicts"] = result.verdicts
            logger.info(f"    [{metric_name}] Verdicts: {result.verdicts}")

        if hasattr(result, 'claims') and result.claims:
            details["claims"] = result.claims
            logger.info(f"    [{metric_name}] Claims extracted: {len(result.claims)}")

        # RAG Tuning: Additional attributes that might be useful
        if hasattr(result, 'questions_generated'):
            details["questions_generated"] = result.questions_generated
        if hasattr(result, 'context_precision_scores'):
            details["per_context_scores"] = result.context_precision_scores
        if hasattr(result, 'sentence_scores'):
            details["sentence_scores"] = result.sentence_scores

        return score, status, elapsed, details

    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        logger.error(f"    [{metric_name}] ✗ TIMEOUT after {elapsed:.1f}s (limit: {timeout}s)")
        logger.error(f"    [{metric_name}] → This could indicate LLM overload or Ollama issues")
        details["error"] = f"TIMEOUT after {elapsed:.1f}s"
        return 0.0, "TIMEOUT", elapsed, details

    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = str(e)[:300]
        logger.error(f"    [{metric_name}] ✗ ERROR after {elapsed:.1f}s: {error_msg}")

        # Log more details for debugging
        if "connection" in error_msg.lower():
            logger.error(f"    [{metric_name}] → Possible Ollama connection issue")
        elif "json" in error_msg.lower() or "parse" in error_msg.lower():
            logger.error(f"    [{metric_name}] → LLM returned unparseable response")
        elif "rate" in error_msg.lower() or "limit" in error_msg.lower():
            logger.error(f"    [{metric_name}] → Rate limiting detected")

        details["error"] = error_msg
        return 0.0, f"ERROR: {error_msg[:100]}", elapsed, details


async def compute_ragas_metrics_for_sample(
    question: str,
    answer: str,
    contexts: list[str],
    ground_truth: str,
    ragas_llm: Any,
    ragas_embeddings: Any,
) -> tuple[RAGASMetricsResult, dict]:
    """Compute RAGAS metrics for a single sample with detailed logging.

    RAGAS 0.4.2: Use async metric scoring with ascore().

    Sprint 79.8.1: Increased timeout to 240s per metric (GPT-OSS:20b needs ~47s/metric).
    Total per sample: ~200s for all 4 metrics.

    Sprint 79 Enhanced: Added per-metric logging to diagnose LLM judging issues.
    Each metric is computed individually with detailed timing and error reporting.

    RAG Tuning: Returns detailed breakdown for each metric including claims, verdicts,
    and LLM reasoning for systematic optimization.

    Args:
        question: User question
        answer: Generated answer
        contexts: Retrieved contexts
        ground_truth: Ground truth answer
        ragas_llm: LLM instance from llm_factory()
        ragas_embeddings: Embeddings from OllamaEmbeddings (async)

    Returns:
        Tuple of (RAGASMetricsResult, rag_tuning_details_dict)
    """
    # Initialize metrics (RAGAS 0.4.2 Collections API)
    context_precision = ContextPrecision(llm=ragas_llm, embeddings=ragas_embeddings)
    context_recall = ContextRecall(llm=ragas_llm, embeddings=ragas_embeddings)
    faithfulness = Faithfulness(llm=ragas_llm)
    answer_relevancy = AnswerRelevancy(llm=ragas_llm, embeddings=ragas_embeddings)

    # Sprint 79.8.1: Added asyncio.wait_for with 240s timeout per metric
    metric_timeout = 240.0  # 240s per metric (GPT-OSS:20b measured at ~47s/metric)

    logger.info(f"  Computing 4 RAGAS metrics (timeout: {metric_timeout}s each)...")

    # RAG Tuning: Collect all metric details
    rag_tuning_details = {
        "metric_timing": {},
        "metric_status": {},
        "metric_details": {},
    }

    # 1. Context Precision: uses reference (ground truth)
    logger.info(f"  [1/4] Context Precision - Checking if retrieved contexts are relevant...")
    cp_score, cp_status, cp_time, cp_details = await compute_single_metric(
        metric_name="ContextPrecision",
        metric_func=context_precision.ascore,
        metric_kwargs={
            "user_input": question,
            "reference": ground_truth,
            "retrieved_contexts": contexts,
        },
        timeout=metric_timeout,
    )
    rag_tuning_details["metric_timing"]["context_precision"] = cp_time
    rag_tuning_details["metric_status"]["context_precision"] = cp_status
    rag_tuning_details["metric_details"]["context_precision"] = cp_details

    # 2. Context Recall: uses reference (ground truth)
    logger.info(f"  [2/4] Context Recall - Checking if all needed contexts were retrieved...")
    cr_score, cr_status, cr_time, cr_details = await compute_single_metric(
        metric_name="ContextRecall",
        metric_func=context_recall.ascore,
        metric_kwargs={
            "user_input": question,
            "retrieved_contexts": contexts,
            "reference": ground_truth,
        },
        timeout=metric_timeout,
    )
    rag_tuning_details["metric_timing"]["context_recall"] = cr_time
    rag_tuning_details["metric_status"]["context_recall"] = cr_status
    rag_tuning_details["metric_details"]["context_recall"] = cr_details

    # 3. Faithfulness: uses response (generated answer)
    logger.info(f"  [3/4] Faithfulness - Checking if answer is grounded in contexts...")
    f_score, f_status, f_time, f_details = await compute_single_metric(
        metric_name="Faithfulness",
        metric_func=faithfulness.ascore,
        metric_kwargs={
            "user_input": question,
            "response": answer,
            "retrieved_contexts": contexts,
        },
        timeout=metric_timeout,
    )
    rag_tuning_details["metric_timing"]["faithfulness"] = f_time
    rag_tuning_details["metric_status"]["faithfulness"] = f_status
    rag_tuning_details["metric_details"]["faithfulness"] = f_details

    # 4. Answer Relevancy: uses only response (no contexts!)
    logger.info(f"  [4/4] Answer Relevancy - Checking if answer addresses the question...")
    ar_score, ar_status, ar_time, ar_details = await compute_single_metric(
        metric_name="AnswerRelevancy",
        metric_func=answer_relevancy.ascore,
        metric_kwargs={
            "user_input": question,
            "response": answer,
        },
        timeout=metric_timeout,
    )
    rag_tuning_details["metric_timing"]["answer_relevancy"] = ar_time
    rag_tuning_details["metric_status"]["answer_relevancy"] = ar_status
    rag_tuning_details["metric_details"]["answer_relevancy"] = ar_details

    # Log summary
    total_time = cp_time + cr_time + f_time + ar_time
    rag_tuning_details["total_metric_time"] = total_time
    logger.info(f"  Metrics Summary:")
    logger.info(f"    CP: {cp_score:.3f} ({cp_status}) | CR: {cr_score:.3f} ({cr_status})")
    logger.info(f"    F:  {f_score:.3f} ({f_status}) | AR: {ar_score:.3f} ({ar_status})")
    logger.info(f"    Total metric time: {total_time:.1f}s")

    # Warn if any metrics failed
    failed_metrics = []
    if cp_status != "OK":
        failed_metrics.append(f"ContextPrecision ({cp_status})")
    if cr_status != "OK":
        failed_metrics.append(f"ContextRecall ({cr_status})")
    if f_status != "OK":
        failed_metrics.append(f"Faithfulness ({f_status})")
    if ar_status != "OK":
        failed_metrics.append(f"AnswerRelevancy ({ar_status})")

    if failed_metrics:
        logger.warning(f"  ⚠️ Failed metrics: {', '.join(failed_metrics)}")
        logger.warning(f"  → Zero scores may indicate LLM judging issues, not retrieval quality!")
        rag_tuning_details["failed_metrics"] = failed_metrics

    result = RAGASMetricsResult(
        context_precision=cp_score,
        context_recall=cr_score,
        faithfulness=f_score,
        answer_relevancy=ar_score,
    )

    return result, rag_tuning_details


async def run_ragas_evaluation(
    dataset_path: str = "data/evaluation/ragas_dataset.jsonl",
    namespace_id: str = "ragas_eval",
    mode: str = "hybrid",
    max_questions: int = -1,
    output_dir: str = "data/evaluation/results",
    use_ground_truth: bool = False,
) -> dict[str, Any]:
    """Run RAGAS evaluation on AegisRAG system.

    Sprint 79 POC Feature 79.10: Proof-of-concept workaround to demonstrate RAGAS works
    when given real answers. This bypasses API response and uses ground_truth instead.

    Args:
        dataset_path: Path to RAGAS JSONL dataset
        namespace_id: Namespace for retrieval filtering
        mode: Retrieval mode (vector, hybrid, graph)
        max_questions: Max questions to evaluate (-1 = all)
        output_dir: Directory to save results
        use_ground_truth: If True, use ground_truth as answer instead of API response (POC mode)

    Returns:
        Evaluation results with all 4 RAGAS metrics
    """
    logger.info("=" * 80)
    if use_ground_truth:
        logger.info(f"RAGAS EVALUATION - Sprint 79 POC 79.10 (RAGAS 0.4.2 + Ground Truth)")
    else:
        logger.info(f"RAGAS EVALUATION - Sprint 79 Feature 79.8 (RAGAS 0.4.2)")
    logger.info("=" * 80)
    logger.info(f"Dataset: {dataset_path}")
    logger.info(f"Namespace: {namespace_id}")
    logger.info(f"Mode: {mode}")
    if use_ground_truth:
        logger.info(f"POC Mode: Using ground_truth as answer (bypassing API)")
    else:
        logger.info(f"Mode: Using API responses as answers")

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
            # Sprint 79 POC 79.10: If use_ground_truth flag set, skip API and use ground_truth
            if use_ground_truth:
                logger.info(f"  POC Mode: Using ground_truth as answer (skipping API query)")
                response = {
                    "answer": ground_truth,
                    "contexts": expected_contexts,  # Use expected contexts from dataset
                    "sources": [{"text": ctx} for ctx in expected_contexts],
                    "mode": mode,
                    "question": question,
                }
                query_time = 0.0  # No API call in POC mode
            else:
                # Query system normally
                query_start = time.time()
                response = await query_aegis_rag(
                    question=question,
                    namespace_id=namespace_id,
                    mode=mode,
                )
                query_time = time.time() - query_start

            # Collect for RAGAS evaluation
            # RAG Tuning: Include full context texts and metadata for analysis
            result = {
                "question": question,
                "answer": response["answer"],
                "contexts": response["contexts"],  # Full context texts
                "ground_truth": ground_truth,
                "expected_contexts": expected_contexts,
                "mode": mode,
                "query_time": query_time,
                "num_contexts_retrieved": len(response["contexts"]),
                "poc_mode": use_ground_truth,
                # RAG Tuning: Additional data for optimization analysis
                "source_metadata": response.get("source_metadata", []),  # Chunk IDs, scores, etc.
                "full_context_texts": response["contexts"],  # Keep full texts for analysis
            }
            results.append(result)

            # Log retrieved sources for RAG Tuning visibility
            logger.info(f"  ✓ Answer: {response['answer'][:100]}...")
            logger.info(f"  Retrieved {len(response['contexts'])} contexts in {query_time:.2f}s")
            # RAG Tuning: Log source details
            if response.get("source_metadata"):
                for src in response["source_metadata"][:3]:  # Log first 3 sources
                    logger.info(f"    - [{src.get('index', '?')}] {src.get('filename', 'unknown')[:40]} "
                               f"(score: {src.get('score', 'N/A')}, len: {src.get('text_length', 0)})")

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
                "poc_mode": use_ground_truth,
            })

    total_query_time = time.time() - start_time

    # Compute RAGAS metrics
    logger.info("\n" + "=" * 80)
    logger.info("COMPUTING RAGAS METRICS (0.4.2 API)")
    logger.info("=" * 80)
    logger.info("Using GPT-OSS:20b (Ollama) for LLM-based metrics...")

    # Get LLM and embeddings for RAGAS (RAGAS 0.4.2)
    ragas_llm = get_ragas_llm()
    ragas_embeddings = get_ragas_embeddings()

    # Track metrics per sample
    all_metrics = []
    metrics_start_time = time.time()

    try:
        # RAGAS 0.4.2: Compute metrics for each sample individually
        for i, result in enumerate(results):
            logger.info(f"\n{'='*60}")
            logger.info(f"Computing metrics for sample {i+1}/{len(results)}")
            logger.info(f"{'='*60}")

            # Log question, answer, ground truth for manual verification (min 300 chars)
            q_truncated = result["question"][:300] + "..." if len(result["question"]) > 300 else result["question"]
            a_truncated = result["answer"][:400] + "..." if len(result["answer"]) > 400 else result["answer"]
            gt_truncated = result["ground_truth"][:400] + "..." if len(result["ground_truth"]) > 400 else result["ground_truth"]

            logger.info(f"  Q: {q_truncated}")
            logger.info(f"  A: {a_truncated}")
            logger.info(f"  GT: {gt_truncated}")
            logger.info(f"  Contexts: {len(result['contexts'])} retrieved, "
                       f"total {sum(len(c) for c in result['contexts'])} chars")

            sample_start = time.time()
            # RAG Tuning: Returns tuple of (metrics, rag_tuning_details)
            sample_metrics, rag_tuning_details = await compute_ragas_metrics_for_sample(
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
            result["rag_tuning_details"] = rag_tuning_details  # RAG Tuning: Save details

            logger.info(f"  ✓ Metrics computed in {sample_time:.2f}s")
            logger.info(f"  SCORES: CP={sample_metrics.context_precision:.3f} | "
                       f"CR={sample_metrics.context_recall:.3f} | "
                       f"F={sample_metrics.faithfulness:.3f} | "
                       f"AR={sample_metrics.answer_relevancy:.3f}")

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

    # Sprint 79 POC 79.10: Mark POC results with special naming
    poc_suffix = "_poc_ground_truth" if use_ground_truth else ""
    results_file = output_path / f"ragas_eval_{mode}{poc_suffix}_{timestamp}.json"

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
            "poc_mode": use_ground_truth,
            "poc_description": "Sprint 79 POC 79.10: Using ground_truth as answer to prove RAGAS metrics work" if use_ground_truth else None,
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
    if use_ground_truth:
        logger.info(f"Test Type: POC (Sprint 79.10) - Ground Truth Mode")
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

    if use_ground_truth:
        logger.info(f"\nPOC MODE INTERPRETATION:")
        logger.info(f"  Context Precision/Recall are measuring retrieval quality against expected contexts")
        logger.info(f"  Faithfulness measures: Is ground_truth faithful to retrieved contexts? (should be high)")
        logger.info(f"  Answer Relevancy measures: Is ground_truth relevant to the question? (should be high)")
        logger.info(f"\nExpected Results in POC mode:")
        logger.info(f"  - Faithfulness should be >0.5 (proves RAGAS can evaluate real answers)")
        logger.info(f"  - Answer Relevancy should be >0.5 (proves RAGAS can evaluate real answers)")

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
    parser.add_argument(
        "--use-ground-truth",
        action="store_true",
        help="POC Mode (Sprint 79.10): Use ground_truth as answer instead of API response. "
             "This proves RAGAS works when given real answers. Bypasses API queries.",
    )

    args = parser.parse_args()

    # Run evaluation
    await run_ragas_evaluation(
        dataset_path=args.dataset,
        namespace_id=args.namespace,
        mode=args.mode,
        max_questions=args.max_questions,
        output_dir=args.output_dir,
        use_ground_truth=args.use_ground_truth,
    )


if __name__ == "__main__":
    asyncio.run(main())
