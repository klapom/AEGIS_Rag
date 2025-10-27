"""Custom RAG Evaluation Metrics using Ollama LLM.

This module provides custom implementations of RAGAS-like evaluation metrics
that work directly with Ollama, avoiding library compatibility issues.

Metrics implemented:
- Context Precision: Relevance of retrieved contexts
- Context Recall: Coverage of ground truth in contexts
- Faithfulness: Grounding of response in contexts (hallucination detection)

Sprint 8: Alternative to RAGAS library for E2E testing
"""

import asyncio
from typing import Any

import structlog
from ollama import AsyncClient
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class MetricResult(BaseModel):
    """Result from a single metric evaluation.

    Attributes:
        score: Metric score (0.0 to 1.0)
        details: Additional details about the evaluation
    """

    score: float = Field(..., ge=0.0, le=1.0, description="Metric score")
    details: dict[str, Any] = Field(default_factory=dict, description="Evaluation details")


class EvaluationResults(BaseModel):
    """Combined evaluation results for all metrics.

    Attributes:
        context_precision: Precision score
        context_recall: Recall score
        faithfulness: Faithfulness score
        metadata: Evaluation metadata
    """

    context_precision: float = Field(..., ge=0.0, le=1.0)
    context_recall: float = Field(..., ge=0.0, le=1.0)
    faithfulness: float = Field(..., ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CustomMetricsEvaluator:
    """Custom RAG evaluation metrics using Ollama LLM.

    Provides RAGAS-like evaluation without external library dependencies.
    Uses Ollama for LLM-based evaluation of retrieval quality.

    Example:
        >>> evaluator = CustomMetricsEvaluator()
        >>> results = await evaluator.evaluate_all(
        ...     query="What is RAG?",
        ...     retrieved_contexts=["RAG combines retrieval..."],
        ...     response="RAG is a technique...",
        ...     ground_truth="RAG combines retrieval and generation."
        ... )
        >>> print(f"Precision: {results.context_precision:.3f}")
    """

    def __init__(
        self,
        model: str = "qwen3:0.6b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.0,
    ):
        """Initialize Custom Metrics Evaluator.

        Args:
            model: Ollama model name
            base_url: Ollama server URL
            temperature: LLM temperature (0.0 for deterministic)
        """
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.client = AsyncClient(host=base_url)

        logger.info(
            "custom_metrics_evaluator_initialized",
            model=model,
            base_url=base_url,
        )

    async def _generate(self, prompt: str) -> str:
        """Generate response from Ollama.

        Args:
            prompt: Input prompt

        Returns:
            Generated text response
        """
        response = await self.client.generate(
            model=self.model,
            prompt=prompt,
            options={"temperature": self.temperature},
        )
        return response["response"].strip()

    async def evaluate_context_precision(
        self,
        query: str,
        retrieved_contexts: list[str],
        ground_truth: str,
    ) -> MetricResult:
        """Evaluate Context Precision: Relevance of retrieved contexts.

        For each retrieved context, asks LLM if it's relevant to answering
        the query. Precision = relevant_count / total_count

        Args:
            query: User query
            retrieved_contexts: List of retrieved document texts
            ground_truth: Reference answer (for context)

        Returns:
            MetricResult with precision score (0.0 to 1.0)

        Example:
            Query: "What is RAG?"
            Contexts: ["RAG combines...", "Weather is sunny"]
            → Score: 0.5 (1 relevant / 2 total)
        """
        if not retrieved_contexts:
            return MetricResult(score=0.0, details={"total": 0, "relevant": 0})

        logger.info(
            "evaluating_context_precision",
            query=query[:50],
            num_contexts=len(retrieved_contexts),
        )

        relevant_count = 0
        relevance_results = []

        for i, context in enumerate(retrieved_contexts):
            prompt = f"""Is the following context relevant for answering the given question?

Question: {query}

Context: {context}

Answer ONLY with "YES" or "NO"."""

            response = await self._generate(prompt)
            is_relevant = "YES" in response.upper()

            if is_relevant:
                relevant_count += 1

            relevance_results.append(
                {"context_idx": i, "relevant": is_relevant, "response": response}
            )

        precision = relevant_count / len(retrieved_contexts)

        logger.info(
            "context_precision_evaluated",
            precision=precision,
            relevant=relevant_count,
            total=len(retrieved_contexts),
        )

        return MetricResult(
            score=precision,
            details={
                "total": len(retrieved_contexts),
                "relevant": relevant_count,
                "results": relevance_results,
            },
        )

    async def evaluate_context_recall(
        self,
        ground_truth: str,
        retrieved_contexts: list[str],
    ) -> MetricResult:
        """Evaluate Context Recall: Coverage of ground truth in contexts.

        Decomposes ground truth into statements, then checks if each
        statement can be attributed to the retrieved contexts.
        Recall = attributable_statements / total_statements

        Args:
            ground_truth: Reference answer
            retrieved_contexts: List of retrieved document texts

        Returns:
            MetricResult with recall score (0.0 to 1.0)

        Example:
            Ground Truth: "RAG uses retrieval. RAG uses generation."
            Contexts: ["RAG uses retrieval for better answers"]
            → Score: 0.5 (1 attributable / 2 statements)
        """
        if not ground_truth.strip():
            return MetricResult(score=1.0, details={"statements": 0, "attributable": 0})

        logger.info("evaluating_context_recall", ground_truth=ground_truth[:50])

        # Step 1: Decompose ground truth into statements
        split_prompt = f"""Break down the following text into individual factual statements (one per line):

{ground_truth}

List the statements (one per line):"""

        statements_response = await self._generate(split_prompt)
        statements = [s.strip() for s in statements_response.split("\n") if s.strip()]

        if not statements:
            return MetricResult(score=1.0, details={"statements": 0, "attributable": 0})

        # Step 2: Check if each statement is attributable
        attributable_count = 0
        combined_contexts = "\n\n".join(retrieved_contexts)
        attribution_results = []

        for i, statement in enumerate(statements):
            prompt = f"""Can the following statement be inferred from the given contexts?

Statement: {statement}

Contexts:
{combined_contexts}

Answer ONLY with "YES" or "NO"."""

            response = await self._generate(prompt)
            is_attributable = "YES" in response.upper()

            if is_attributable:
                attributable_count += 1

            attribution_results.append(
                {
                    "statement_idx": i,
                    "statement": statement,
                    "attributable": is_attributable,
                    "response": response,
                }
            )

        recall = attributable_count / len(statements)

        logger.info(
            "context_recall_evaluated",
            recall=recall,
            attributable=attributable_count,
            total=len(statements),
        )

        return MetricResult(
            score=recall,
            details={
                "statements": len(statements),
                "attributable": attributable_count,
                "results": attribution_results,
            },
        )

    async def evaluate_faithfulness(
        self,
        response: str,
        retrieved_contexts: list[str],
    ) -> MetricResult:
        """Evaluate Faithfulness: Grounding of response in contexts.

        Decomposes response into claims, then checks if each claim can be
        verified from the retrieved contexts (hallucination detection).
        Faithfulness = verified_claims / total_claims

        Args:
            response: Generated answer
            retrieved_contexts: List of retrieved document texts

        Returns:
            MetricResult with faithfulness score (0.0 to 1.0)

        Example:
            Response: "RAG uses retrieval. RAG was invented in 2025."
            Contexts: ["RAG uses retrieval for better answers"]
            → Score: 0.5 (1 verified / 2 claims) - second claim is hallucination
        """
        if not response.strip():
            return MetricResult(score=1.0, details={"claims": 0, "verified": 0})

        logger.info("evaluating_faithfulness", response=response[:50])

        # Step 1: Decompose response into claims
        split_prompt = f"""Break down the following answer into individual claims/assertions (one per line):

{response}

List the claims (one per line):"""

        claims_response = await self._generate(split_prompt)
        claims = [c.strip() for c in claims_response.split("\n") if c.strip()]

        if not claims:
            return MetricResult(score=1.0, details={"claims": 0, "verified": 0})

        # Step 2: Verify each claim against contexts
        verified_count = 0
        combined_contexts = "\n\n".join(retrieved_contexts)
        verification_results = []

        for i, claim in enumerate(claims):
            prompt = f"""Can the following claim be verified from the given contexts?

Claim: {claim}

Contexts:
{combined_contexts}

Answer ONLY with "YES" or "NO"."""

            response_text = await self._generate(prompt)
            is_verified = "YES" in response_text.upper()

            if is_verified:
                verified_count += 1

            verification_results.append(
                {
                    "claim_idx": i,
                    "claim": claim,
                    "verified": is_verified,
                    "response": response_text,
                }
            )

        faithfulness = verified_count / len(claims)

        logger.info(
            "faithfulness_evaluated",
            faithfulness=faithfulness,
            verified=verified_count,
            total=len(claims),
        )

        return MetricResult(
            score=faithfulness,
            details={
                "claims": len(claims),
                "verified": verified_count,
                "results": verification_results,
            },
        )

    async def evaluate_all(
        self,
        query: str,
        retrieved_contexts: list[str],
        response: str,
        ground_truth: str,
    ) -> EvaluationResults:
        """Evaluate all metrics: Precision, Recall, Faithfulness.

        Runs all three evaluations in parallel for efficiency.

        Args:
            query: User query
            retrieved_contexts: Retrieved document texts
            response: Generated answer
            ground_truth: Reference answer

        Returns:
            EvaluationResults with all metric scores

        Example:
            >>> results = await evaluator.evaluate_all(
            ...     query="What is RAG?",
            ...     retrieved_contexts=["RAG combines retrieval and generation"],
            ...     response="RAG is a retrieval-augmented generation technique",
            ...     ground_truth="RAG combines retrieval with generation"
            ... )
        """
        logger.info(
            "evaluating_all_metrics",
            query=query[:50],
            num_contexts=len(retrieved_contexts),
        )

        # Run all evaluations in parallel
        precision_task = self.evaluate_context_precision(query, retrieved_contexts, ground_truth)
        recall_task = self.evaluate_context_recall(ground_truth, retrieved_contexts)
        faithfulness_task = self.evaluate_faithfulness(response, retrieved_contexts)

        precision_result, recall_result, faithfulness_result = await asyncio.gather(
            precision_task, recall_task, faithfulness_task
        )

        results = EvaluationResults(
            context_precision=precision_result.score,
            context_recall=recall_result.score,
            faithfulness=faithfulness_result.score,
            metadata={
                "model": self.model,
                "evaluator": "custom_ollama",
                "precision_details": precision_result.details,
                "recall_details": recall_result.details,
                "faithfulness_details": faithfulness_result.details,
            },
        )

        logger.info(
            "all_metrics_evaluated",
            precision=results.context_precision,
            recall=results.context_recall,
            faithfulness=results.faithfulness,
        )

        return results


# Export public API
__all__ = [
    "CustomMetricsEvaluator",
    "EvaluationResults",
    "MetricResult",
]
