"""LLM-based answer generation for RAG.

Sprint 11: Feature 11.1 - LLM-Based Answer Generation
Replaces simple_answer_node placeholder with proper LLM generation.
"""

from typing import Any

import structlog
from langchain_ollama import ChatOllama

from src.core.config import settings
from src.prompts.answer_prompts import (
    ANSWER_GENERATION_PROMPT,
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
    """

    def __init__(self, model_name: str | None = None, temperature: float = 0.0):
        """Initialize answer generator.

        Args:
            model_name: Ollama model name (default: llama3.2:3b from ollama_model_query)
            temperature: LLM temperature for answer generation (0.0 = deterministic)
        """
        self.model_name = model_name or settings.ollama_model_query
        self.temperature = temperature
        self.llm = ChatOllama(
            model=self.model_name,
            temperature=self.temperature,
            base_url=settings.ollama_base_url,
        )

        logger.info(
            "answer_generator_initialized",
            model=self.model_name,
            temperature=self.temperature,
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
            prompt = MULTI_HOP_REASONING_PROMPT.format(
                contexts=context_text, query=query
            )
        else:
            prompt = ANSWER_GENERATION_PROMPT.format(context=context_text, query=query)

        # Generate answer
        logger.debug("generating_answer", query=query[:100], contexts_count=len(contexts))

        try:
            response = await self.llm.ainvoke(prompt)
            answer = response.content.strip()

            logger.info(
                "answer_generated",
                query=query[:100],
                answer_length=len(answer),
                contexts_used=len(contexts),
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
