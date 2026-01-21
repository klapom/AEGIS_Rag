"""Eval Harness for automated quality gates in RAG pipeline.

Sprint 67 Feature 67.6: Automated validation for grounding, citation coverage, and format compliance.

This module provides automated quality checks for RAG responses to ensure:
- Answer grounding: Verify claims are supported by sources
- Citation coverage: Ensure all claims have proper citations
- Format compliance: Validate markdown structure and citation format

Architecture:
    Query + Answer + Sources → EvalHarness → [EvalResult] → Quality Gates

Integration:
    - Uses UnifiedTracer (Feature 67.5) for trace data
    - Uses AegisLLMProxy for grounding checks
    - Returns detailed failure reasons for debugging

Performance Requirements:
    - Format check: <100ms (regex-based, no LLM)
    - Citation coverage: <100ms (parsing-based, no LLM)
    - Grounding check: <500ms (LLM-based validation)

Example:
    >>> harness = EvalHarness()
    >>> results = await harness.evaluate_response(
    ...     query="What is RAG?",
    ...     answer="RAG is Retrieval Augmented Generation [1][2].",
    ...     sources=[{"chunk_id": "c1", "text": "RAG definition..."}, ...]
    ... )
    >>> all_passed = all(r.passed for r in results)
    >>> print(f"All checks passed: {all_passed}")

Related:
    - Feature 67.5: Unified Trace & Telemetry
    - ADR-067: Eval Harness Design
    - Paper 2512.16301: Tool-Level Adaptation
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from src.core.exceptions import EvaluationError, LLMExecutionError
from src.domains.llm_integration.config import get_llm_proxy_config
from src.domains.llm_integration.models import (
    Complexity,
    DataClassification,
    LLMTask,
    QualityRequirement,
    TaskType,
)
from src.domains.llm_integration.proxy.aegis_llm_proxy import AegisLLMProxy

logger = structlog.get_logger(__name__)


class QualityCheck(str, Enum):
    """Quality check types for RAG responses.

    Each check validates a different aspect of the response quality:
    - GROUNDING: Verify answer is supported by sources (LLM-based)
    - CITATION_COVERAGE: Check all claims have citations (parsing-based)
    - FORMAT_COMPLIANCE: Validate markdown structure (regex-based)
    """

    GROUNDING = "grounding"
    CITATION_COVERAGE = "citation_coverage"
    FORMAT_COMPLIANCE = "format_compliance"


@dataclass
class EvalResult:
    """Result of a single quality check.

    Attributes:
        check: Type of quality check performed
        passed: Whether the check passed the threshold
        score: Numeric score (0.0-1.0), higher is better
        details: Additional details about the check (failures, warnings, etc.)
        latency_ms: Time taken to perform the check
    """

    check: QualityCheck
    passed: bool
    score: float
    details: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0

    def __repr__(self) -> str:
        """Human-readable representation."""
        status = "PASS" if self.passed else "FAIL"
        return (
            f"EvalResult({self.check.value}: {status}, "
            f"score={self.score:.3f}, latency={self.latency_ms:.1f}ms)"
        )


class EvalHarness:
    """Automated quality gates for RAG pipeline.

    This harness runs multiple quality checks on RAG responses and returns
    detailed results for each check. Configurable thresholds allow tuning
    the strictness of each check.

    Attributes:
        thresholds: Minimum score required for each check to pass
        llm_proxy: AegisLLMProxy instance for grounding checks (optional)

    Example:
        >>> # Default thresholds
        >>> harness = EvalHarness()
        >>> results = await harness.evaluate_response(query, answer, sources)

        >>> # Custom thresholds
        >>> harness = EvalHarness(thresholds={
        ...     QualityCheck.GROUNDING: 0.9,  # Stricter
        ...     QualityCheck.CITATION_COVERAGE: 0.6,  # More lenient
        ...     QualityCheck.FORMAT_COMPLIANCE: 0.95
        ... })
    """

    # Default thresholds for quality checks
    DEFAULT_THRESHOLDS = {
        QualityCheck.GROUNDING: 0.8,  # 80% of claims must be grounded
        QualityCheck.CITATION_COVERAGE: 0.7,  # 70% of claims must be cited
        QualityCheck.FORMAT_COMPLIANCE: 0.95,  # 95% format compliance
    }

    # Citation pattern: [1], [2][3], etc.
    CITATION_PATTERN = re.compile(r"\[(\d+)\]")

    # Markdown validation patterns
    INVALID_MARKDOWN_PATTERNS = [
        (r"^\s*#+\s*$", "Empty heading"),  # Empty headings (## )
        (r"^\s*[-*+]\s*$", "Empty list item"),  # Empty list items (- )
        (r"\[([^\]]*)\]\(\s*\)", "Empty link"),  # Empty links [text]()
        (r"```\s*$", "Unclosed code block"),  # Unclosed code blocks
    ]

    def __init__(
        self,
        thresholds: dict[QualityCheck, float] | None = None,
        llm_proxy: AegisLLMProxy | None = None,
    ):
        """Initialize EvalHarness.

        Args:
            thresholds: Custom thresholds for quality checks.
                       If None, uses DEFAULT_THRESHOLDS.
            llm_proxy: Pre-configured AegisLLMProxy instance.
                      If None, creates a new instance lazily when needed.
        """
        self.logger = structlog.get_logger(__name__)
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS.copy()
        self._llm_proxy = llm_proxy

        # Validate thresholds
        for check, threshold in self.thresholds.items():
            if not 0.0 <= threshold <= 1.0:
                raise ValueError(
                    f"Threshold for {check.value} must be between 0.0 and 1.0, "
                    f"got {threshold}"
                )

        self.logger.info(
            "eval_harness_initialized",
            thresholds={k.value: v for k, v in self.thresholds.items()},
        )

    @property
    def llm_proxy(self) -> AegisLLMProxy:
        """Get or create LLM proxy instance (lazy initialization)."""
        if self._llm_proxy is None:
            config = get_llm_proxy_config()
            self._llm_proxy = AegisLLMProxy(config)
        return self._llm_proxy

    async def evaluate_response(
        self,
        query: str,
        answer: str,
        sources: list[dict[str, Any]],
    ) -> list[EvalResult]:
        """Run all quality checks on RAG response.

        This is the main entry point for the eval harness. It runs all three
        quality checks (format, citation, grounding) and returns results for each.

        Args:
            query: Original user query
            answer: Generated answer to evaluate
            sources: List of source documents with format:
                    [{"chunk_id": "c1", "text": "...", "score": 0.9}, ...]

        Returns:
            List of EvalResult, one for each quality check

        Raises:
            EvaluationError: If evaluation fails critically

        Example:
            >>> results = await harness.evaluate_response(
            ...     query="What is RAG?",
            ...     answer="RAG is Retrieval Augmented Generation [1][2].",
            ...     sources=[
            ...         {"chunk_id": "c1", "text": "RAG definition..."},
            ...         {"chunk_id": "c2", "text": "RAG architecture..."}
            ...     ]
            ... )
            >>> for result in results:
            ...     print(f"{result.check}: {'PASS' if result.passed else 'FAIL'}")
        """
        start_time = time.perf_counter()

        try:
            # Run checks in parallel for better performance
            # Note: We run them sequentially for now, but could use asyncio.gather
            results = []

            # Check 1: Format Compliance (fast, no LLM)
            format_result = await self._check_format(answer)
            results.append(format_result)

            # Check 2: Citation Coverage (fast, no LLM)
            coverage_result = await self._check_citation_coverage(answer, sources)
            results.append(coverage_result)

            # Check 3: Grounding (slower, uses LLM)
            grounding_result = await self._check_grounding(answer, sources)
            results.append(grounding_result)

            total_latency = (time.perf_counter() - start_time) * 1000
            self.logger.info(
                "eval_response_completed",
                query_length=len(query),
                answer_length=len(answer),
                source_count=len(sources),
                results={r.check.value: r.passed for r in results},
                total_latency_ms=total_latency,
            )

            return results

        except Exception as e:
            self.logger.exception(
                "eval_response_failed",
                query=query[:100],
                error=str(e),
            )
            raise EvaluationError(
                message=f"Evaluation failed: {str(e)}",
                details={"query": query[:100], "error": str(e)},
            ) from e

    async def _check_format(self, answer: str) -> EvalResult:
        """Validate markdown format compliance.

        Checks:
        - No empty headings (## )
        - No empty list items (- )
        - No empty links [text]()
        - No unclosed code blocks
        - Citations use correct format [1][2]

        Performance: <100ms (regex-based, no LLM)

        Args:
            answer: Generated answer to validate

        Returns:
            EvalResult with format compliance score
        """
        start_time = time.perf_counter()
        issues = []

        # Check for invalid markdown patterns
        for pattern, description in self.INVALID_MARKDOWN_PATTERNS:
            matches = re.findall(pattern, answer, re.MULTILINE)
            if matches:
                issues.append(
                    {
                        "type": description,
                        "count": len(matches),
                        "examples": matches[:3],  # First 3 examples
                    }
                )

        # Check citation format
        citation_matches = self.CITATION_PATTERN.findall(answer)
        if citation_matches:
            # Verify citations are sequential (1, 2, 3, not 1, 3, 5)
            # Sprint 118 Fix: C401 - use set comprehension
            citation_numbers = sorted({int(c) for c in citation_matches})
            expected = list(range(1, len(citation_numbers) + 1))
            if citation_numbers != expected:
                issues.append(
                    {
                        "type": "Non-sequential citations",
                        "found": citation_numbers,
                        "expected": expected,
                    }
                )

        # Calculate score: 1.0 if no issues, decrease by 0.1 per issue type
        score = max(0.0, 1.0 - (len(issues) * 0.1))
        passed = score >= self.thresholds[QualityCheck.FORMAT_COMPLIANCE]
        latency_ms = (time.perf_counter() - start_time) * 1000

        return EvalResult(
            check=QualityCheck.FORMAT_COMPLIANCE,
            passed=passed,
            score=score,
            details={
                "issues": issues,
                "issue_count": len(issues),
                "threshold": self.thresholds[QualityCheck.FORMAT_COMPLIANCE],
            },
            latency_ms=latency_ms,
        )

    async def _check_citation_coverage(
        self,
        answer: str,
        sources: list[dict[str, Any]],
    ) -> EvalResult:
        """Check if all claims have proper citations.

        This check parses citations from the answer and verifies:
        1. All cited numbers map to valid sources
        2. Major claims have citations
        3. Citation distribution is reasonable

        Performance: <100ms (parsing-based, no LLM)

        Args:
            answer: Generated answer with citations
            sources: List of source documents

        Returns:
            EvalResult with citation coverage score
        """
        start_time = time.perf_counter()

        # Extract citations from answer
        citation_matches = self.CITATION_PATTERN.findall(answer)
        # Sprint 118 Fix: C401 - use set comprehension
        cited_numbers = {int(c) for c in citation_matches}

        # Split answer into sentences
        sentences = re.split(r"[.!?]+", answer)
        sentences = [s.strip() for s in sentences if s.strip()]

        # Count sentences with citations
        sentences_with_citations = 0
        for sentence in sentences:
            if self.CITATION_PATTERN.search(sentence):
                sentences_with_citations += 1

        # Calculate metrics
        total_sentences = len(sentences)
        citation_coverage = (
            sentences_with_citations / total_sentences if total_sentences > 0 else 0.0
        )

        # Check if all citations map to valid sources
        max_source_id = len(sources)
        invalid_citations = [c for c in cited_numbers if c > max_source_id or c < 1]

        # Warnings (don't fail, but report)
        warnings = []
        if citation_coverage < 0.5:
            warnings.append(f"Low citation coverage: {citation_coverage:.1%}")
        if invalid_citations:
            warnings.append(f"Invalid citation numbers: {invalid_citations}")
        if not cited_numbers and total_sentences > 1:
            warnings.append("No citations found in multi-sentence answer")

        # Score: citation_coverage, penalized for invalid citations
        score = citation_coverage
        if invalid_citations:
            score *= 0.5  # 50% penalty for invalid citations

        passed = score >= self.thresholds[QualityCheck.CITATION_COVERAGE]
        latency_ms = (time.perf_counter() - start_time) * 1000

        return EvalResult(
            check=QualityCheck.CITATION_COVERAGE,
            passed=passed,
            score=score,
            details={
                "total_sentences": total_sentences,
                "sentences_with_citations": sentences_with_citations,
                "citation_coverage": citation_coverage,
                "cited_numbers": sorted(cited_numbers),
                "invalid_citations": invalid_citations,
                "warnings": warnings,
                "threshold": self.thresholds[QualityCheck.CITATION_COVERAGE],
            },
            latency_ms=latency_ms,
        )

    async def _check_grounding(
        self,
        answer: str,
        sources: list[dict[str, Any]],
    ) -> EvalResult:
        """Verify answer claims are grounded in sources.

        This check uses an LLM to verify that claims in the answer are
        supported by the provided sources. It's the most expensive check
        but provides the highest quality signal.

        Performance: <500ms (LLM-based validation)

        Args:
            answer: Generated answer to validate
            sources: List of source documents

        Returns:
            EvalResult with grounding score

        Raises:
            LLMExecutionError: If LLM call fails
        """
        start_time = time.perf_counter()

        # Build source context
        source_texts = []
        for i, source in enumerate(sources, 1):
            text = source.get("text", source.get("content", ""))
            source_texts.append(f"[{i}] {text[:500]}")  # Truncate to 500 chars

        source_context = "\n\n".join(source_texts)

        # Build grounding check prompt
        prompt = f"""You are a fact-checker. Verify if the ANSWER is grounded in the SOURCES.

ANSWER:
{answer}

SOURCES:
{source_context}

Instructions:
1. Extract all factual claims from the ANSWER
2. For each claim, check if it's supported by SOURCES
3. Rate grounding from 0.0 (no claims grounded) to 1.0 (all claims grounded)
4. Return ONLY a JSON object with this format:

{{
  "grounding_score": 0.85,
  "total_claims": 5,
  "grounded_claims": 4,
  "ungrounded_claims": [
    "Claim that is not supported by sources"
  ],
  "reasoning": "Brief explanation of the score"
}}

IMPORTANT: Return ONLY valid JSON, no other text."""

        try:
            # Create LLM task (use GENERATION since no EVALUATION type exists)
            task = LLMTask(
                task_type=TaskType.GENERATION,
                complexity=Complexity.MEDIUM,
                quality_requirement=QualityRequirement.MEDIUM,
                data_classification=DataClassification.PUBLIC,
                prompt=prompt,
                max_tokens=500,
                temperature=0.0,  # Deterministic for evaluation
            )

            # Call LLM
            response = await self.llm_proxy.generate(task)

            # Parse JSON response
            import json

            try:
                result = json.loads(response.content)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code block
                json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response.content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                else:
                    # Sprint 118 Fix: B904 - raise from None
                    raise ValueError(f"Invalid JSON response: {response.content[:200]}") from None

            score = result.get("grounding_score", 0.0)
            passed = score >= self.thresholds[QualityCheck.GROUNDING]
            latency_ms = (time.perf_counter() - start_time) * 1000

            return EvalResult(
                check=QualityCheck.GROUNDING,
                passed=passed,
                score=score,
                details={
                    "total_claims": result.get("total_claims", 0),
                    "grounded_claims": result.get("grounded_claims", 0),
                    "ungrounded_claims": result.get("ungrounded_claims", []),
                    "reasoning": result.get("reasoning", ""),
                    "threshold": self.thresholds[QualityCheck.GROUNDING],
                    "llm_model": response.model,
                    "llm_latency_ms": response.latency_ms or 0,
                },
                latency_ms=latency_ms,
            )

        except (LLMExecutionError, ValueError, KeyError) as e:
            self.logger.error(
                "grounding_check_failed",
                error=str(e),
                answer_length=len(answer),
                source_count=len(sources),
            )
            # Return failed result instead of raising
            latency_ms = (time.perf_counter() - start_time) * 1000
            return EvalResult(
                check=QualityCheck.GROUNDING,
                passed=False,
                score=0.0,
                details={
                    "error": str(e),
                    "threshold": self.thresholds[QualityCheck.GROUNDING],
                },
                latency_ms=latency_ms,
            )
