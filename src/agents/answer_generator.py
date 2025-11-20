"""LLM-based answer generation for RAG.

Sprint 11: Feature 11.1 - LLM-Based Answer Generation
Sprint 23: Feature 23.6 - AegisLLMProxy Integration
Sprint 27: Feature 27.10 - Inline Source Citations
Migrated from Ollama to multi-cloud LLM proxy (Local → Alibaba Cloud → OpenAI).
"""

import re
from typing import Any

import structlog

from src.components.llm_proxy import get_aegis_llm_proxy
from src.components.llm_proxy.models import (
    Complexity,
    LLMTask,
    QualityRequirement,
    TaskType,
)
from src.core.config import settings
from src.prompts.answer_prompts import (
    ANSWER_GENERATION_PROMPT,
    ANSWER_GENERATION_WITH_CITATIONS_PROMPT,
    MULTI_HOP_REASONING_PROMPT,
)

logger = structlog.get_logger(__name__)


class AnswerGenerator:
    """Generate answers using LLM with retrieved context.

    Features:
    - LLM-based synthesis (not just context concatenation)
    - Source citation support
    - Multi-hop reasoning mode
    - Graceful fallback on errors
    - Multi-cloud routing (Local → Alibaba Cloud → OpenAI) via AegisLLMProxy (Sprint 23)
    """

    def __init__(self, model_name: str | None = None, temperature: float = 0.0) -> None:
        """Initialize answer generator.

        Args:
            model_name: Preferred local model name (default: llama3.2:3b from ollama_model_query)
            temperature: LLM temperature for answer generation (0.0 = deterministic)
        """
        self.model_name = model_name or settings.ollama_model_query
        self.temperature = temperature

        # Sprint 23: Use AegisLLMProxy for multi-cloud routing
        self.proxy = get_aegis_llm_proxy()

        logger.info(
            "answer_generator_initialized",
            model=self.model_name,
            temperature=self.temperature,
            proxy="AegisLLMProxy",
        )

    async def generate_answer(
        self,
        query: str,
        contexts: list[dict[str, Any]],
        mode: str = "simple",
    ) -> str:
        """Generate answer from query and retrieved contexts.

        Args:
            query: User question
            contexts: Retrieved document contexts (list of dicts with 'text' and 'source' keys)
            mode: "simple" or "multi_hop" reasoning mode

        Returns:
            Generated answer string
        """
        if not contexts:
            return self._no_context_answer(query)

        # Format contexts
        context_text = self._format_contexts(contexts)

        # Select prompt based on mode
        if mode == "multi_hop":
            prompt = MULTI_HOP_REASONING_PROMPT.format(contexts=context_text, query=query)
            complexity = Complexity.HIGH  # Multi-hop requires complex reasoning
        else:
            prompt = ANSWER_GENERATION_PROMPT.format(context=context_text, query=query)
            complexity = Complexity.MEDIUM  # Simple synthesis

        # Generate answer
        logger.debug("generating_answer", query=query[:100], contexts_count=len(contexts))

        try:
            # Sprint 23: Use AegisLLMProxy for generation
            task = LLMTask(
                task_type=TaskType.GENERATION,
                prompt=prompt,
                quality_requirement=QualityRequirement.MEDIUM,
                complexity=complexity,
                temperature=self.temperature,
                model_local=self.model_name,
            )

            response = await self.proxy.generate(task)
            answer = response.content.strip()

            logger.info(
                "answer_generated",
                query=query[:100],
                answer_length=len(answer),
                contexts_used=len(contexts),
                provider=response.provider,
                cost_usd=response.cost_usd,
                latency_ms=response.latency_ms,
            )

            return answer

        except Exception as e:
            logger.error("answer_generation_failed", query=query[:100], error=str(e))
            return self._fallback_answer(query, contexts)

    def _format_contexts(self, contexts: list[dict[str, Any]]) -> str:
        """Format contexts for prompt.

        Args:
            contexts: List of context dicts

        Returns:
            Formatted context string
        """
        formatted = []
        for i, ctx in enumerate(contexts[:5], 1):  # Top 5 contexts
            text = ctx.get("text", "")
            source = ctx.get("source", "Unknown")
            formatted.append(f"[Context {i} - Source: {source}]\n{text}")
        return "\n\n".join(formatted)

    def _no_context_answer(self, query: str) -> str:
        """Answer when no context retrieved.

        Args:
            query: User question

        Returns:
            Helpful message indicating no information available
        """
        return (
            "I don't have enough information in the knowledge base to answer this question. "
            "Please try rephrasing your question or providing more context."
        )

    def _fallback_answer(self, query: str, contexts: list[dict[str, Any]]) -> str:
        """Fallback answer if LLM generation fails.

        Args:
            query: User question
            contexts: Retrieved contexts

        Returns:
            Simple context concatenation (original behavior)
        """
        context_text = self._format_contexts(contexts)
        return f"Based on the retrieved documents:\n\n{context_text}"

    async def generate_with_citations(
        self,
        query: str,
        contexts: list[dict[str, Any]],
    ) -> tuple[str, dict[int, dict[str, Any]]]:
        """Generate answer with inline source citations.

        Sprint 27 Feature 27.10: Inline Source Citations

        Args:
            query: User question
            contexts: Retrieved document contexts (list of dicts with 'text', 'source', 'title', 'score', 'metadata')

        Returns:
            Tuple of (answer_with_citations, citation_map)
            - answer_with_citations: Generated answer with [1], [2], etc. markers
            - citation_map: Dict mapping citation numbers to source metadata

        Example:
            >>> answer, citations = await generator.generate_with_citations(
            ...     query="What is AEGIS RAG?",
            ...     contexts=[{"text": "AEGIS is a RAG system", "source": "doc.md", ...}]
            ... )
            >>> print(answer)
            "AEGIS RAG is a retrieval system [1] with advanced features."
            >>> print(citations)
            {1: {"text": "AEGIS is a RAG system", "source": "doc.md", ...}}
        """
        # Handle no contexts case
        if not contexts:
            return self._no_context_answer(query), {}

        # Limit to top 10 sources (as per test requirements)
        top_contexts = contexts[:10]

        # Build citation map (always created, even if LLM fails)
        citation_map = self._build_citation_map(top_contexts)

        # Format contexts with source IDs for prompt
        context_text = self._format_contexts_with_citations(top_contexts)

        # Build prompt for citation generation
        prompt = ANSWER_GENERATION_WITH_CITATIONS_PROMPT.format(contexts=context_text, query=query)

        logger.debug(
            "generating_answer_with_citations",
            query=query[:100],
            contexts_count=len(top_contexts),
        )

        try:
            # Use AegisLLMProxy for generation
            task = LLMTask(
                task_type=TaskType.GENERATION,
                prompt=prompt,
                quality_requirement=QualityRequirement.MEDIUM,
                complexity=Complexity.MEDIUM,
                temperature=self.temperature,
                model_local=self.model_name,
            )

            response = await self.proxy.generate(task)
            answer = response.content.strip()

            # Extract cited sources for logging
            cited_sources = self._extract_cited_sources(answer)

            logger.info(
                "answer_with_citations_generated",
                query=query[:100],
                answer_length=len(answer),
                contexts_used=len(top_contexts),
                citations_used=len(cited_sources),
                provider=response.provider,
                cost_usd=response.cost_usd,
                latency_ms=response.latency_ms,
            )

            return answer, citation_map

        except Exception as e:
            logger.error(
                "answer_with_citations_generation_failed",
                query=query[:100],
                error=str(e),
            )
            # Fallback: Return fallback answer but keep citation map
            fallback = self._fallback_answer(query, top_contexts)
            return fallback, citation_map

    def _format_contexts_with_citations(self, contexts: list[dict[str, Any]]) -> str:
        """Format contexts with [Source N] markers for citation prompt.

        Args:
            contexts: List of context dicts

        Returns:
            Formatted context string with source IDs
        """
        formatted = []
        for i, ctx in enumerate(contexts, 1):
            text = ctx.get("text", "")
            source = ctx.get("source", "Unknown")
            title = ctx.get("title", source)
            formatted.append(f"[Source {i}]: {title}\n{text}")
        return "\n\n".join(formatted)

    def _build_citation_map(self, contexts: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
        """Build citation map from contexts.

        Args:
            contexts: List of context dicts (max 10)

        Returns:
            Dict mapping citation number to source metadata
        """
        citation_map = {}
        for i, ctx in enumerate(contexts, 1):
            # Truncate text to 500 chars
            text = ctx.get("text", "")
            truncated_text = text[:500] if len(text) > 500 else text

            citation_map[i] = {
                "text": truncated_text,
                "source": ctx.get("source", "Unknown"),
                "title": ctx.get("title", ctx.get("source", "Unknown")),
                "score": ctx.get("score", 0.0),
                "metadata": ctx.get("metadata", {}),
            }
        return citation_map

    def _extract_cited_sources(self, answer: str) -> set[int]:
        """Extract citation numbers from answer.

        Args:
            answer: Answer text with citations like [1], [2], etc.

        Returns:
            Set of cited source numbers
        """
        matches = re.findall(r"\[(\d+)\]", answer)
        return {int(m) for m in matches}


# Global instance (singleton)
_answer_generator: AnswerGenerator | None = None


def get_answer_generator() -> AnswerGenerator:
    """Get global AnswerGenerator instance (singleton).

    Returns:
        AnswerGenerator instance
    """
    global _answer_generator
    if _answer_generator is None:
        _answer_generator = AnswerGenerator()
    return _answer_generator
