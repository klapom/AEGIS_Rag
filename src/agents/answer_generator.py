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
            model_name: Preferred local model name (default from ollama_model_generation)
            temperature: LLM temperature for answer generation (0.0 = deterministic)
        """
        # Sprint 51 Fix: Use ollama_model_generation (not ollama_model_query) for answer generation
        # ollama_model_generation is configured for RAG answer synthesis (e.g., nemotron-no-think)
        self.model_name = model_name or settings.ollama_model_generation
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

        # Phase 1 Diagnostic Logging: Log full prompt for debugging
        logger.info(
            "CITATIONS_DEBUG_PROMPT",
            prompt_preview=prompt[:2000] if len(prompt) > 2000 else prompt,
            prompt_length=len(prompt),
            query=query,
            contexts_count=len(top_contexts),
            context_text_preview=context_text[:500] if len(context_text) > 500 else context_text,
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

            # Phase 1 Diagnostic Logging: Log full response
            logger.info(
                "CITATIONS_DEBUG_RESPONSE",
                answer_preview=answer[:1000] if len(answer) > 1000 else answer,
                answer_length=len(answer),
                citations_found=list(cited_sources),
                citations_count=len(cited_sources),
                has_citations=len(cited_sources) > 0,
                provider=response.provider,
            )

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

        Sprint 32 Fix: Ensure score and metadata are properly extracted from contexts.
        The contexts come from VectorSearchAgent which includes score and metadata.
        Sprint 51 Fix: Normalize RRF scores to 0-1 range for display.

        Args:
            contexts: List of context dicts (max 10)

        Returns:
            Dict mapping citation number to source metadata
        """
        citation_map = {}

        # Sprint 51 Fix: First pass - collect raw scores to find max for normalization
        raw_scores = []
        for ctx in contexts:
            score = ctx.get("score")
            if score is None or score == 0:
                score = ctx.get(
                    "normalized_rerank_score",
                    ctx.get(
                        "rerank_score",
                        ctx.get("rrf_score", ctx.get("relevance", 0.0)),
                    ),
                )
            try:
                raw_scores.append(float(score) if score is not None else 0.0)
            except (TypeError, ValueError):
                raw_scores.append(0.0)

        # Calculate max score for normalization (avoid division by zero)
        max_score = max(raw_scores) if raw_scores else 1.0
        if max_score <= 0:
            max_score = 1.0

        # Sprint 51 Fix: Detect if scores are RRF scores (typically < 0.1)
        # RRF scores are in the range ~0.016 per ranking list
        # If max score is < 0.1, normalize to 0-1 range
        needs_normalization = max_score < 0.1

        for i, ctx in enumerate(contexts, 1):
            # Truncate text to 500 chars
            text = ctx.get("text", "")
            truncated_text = text[:500] if len(text) > 500 else text

            # Get raw score
            raw_score = raw_scores[i - 1] if i - 1 < len(raw_scores) else 0.0

            # Sprint 51 Fix: Normalize score if needed
            if needs_normalization and max_score > 0:
                # Normalize to 0-1 range where top result is ~0.95
                score = min((raw_score / max_score) * 0.95, 1.0)
            else:
                score = raw_score

            # Sprint 51 Fix: Pass through full metadata from context
            # Metadata now includes document info from Qdrant (source, format, file_size, etc.)
            metadata = ctx.get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {}

            # Add useful fields to metadata if present in context
            if ctx.get("search_type") and "search_type" not in metadata:
                metadata["search_type"] = ctx["search_type"]
            if ctx.get("rank") and "rank" not in metadata:
                metadata["rank"] = ctx["rank"]
            if ctx.get("document_id") and "document_id" not in metadata:
                metadata["document_id"] = ctx["document_id"]

            # Sprint 51 Fix: Clean up metadata - remove None values for cleaner frontend display
            metadata = {k: v for k, v in metadata.items() if v is not None and v != ""}

            citation_map[i] = {
                "text": truncated_text,
                "source": ctx.get("source", "Unknown"),
                "title": ctx.get("title", ctx.get("source", "Unknown")),
                "score": score,
                "metadata": metadata,
                "document_id": ctx.get("document_id", ""),
            }

            # Debug logging to verify data flow
            logger.debug(
                "citation_map_entry_built",
                citation_number=i,
                score=score,
                has_metadata=bool(metadata),
                metadata_keys=list(metadata.keys())[:5] if metadata else [],
                source=ctx.get("source", "Unknown")[:50],
                ctx_keys=list(ctx.keys()),
            )

        logger.info(
            "citation_map_built",
            total_citations=len(citation_map),
            scores=[citation_map[k]["score"] for k in sorted(citation_map.keys())],
        )

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

    async def generate_streaming(
        self,
        query: str,
        contexts: list[dict[str, Any]],
        mode: str = "simple",
    ):
        """Stream LLM response token-by-token.

        Sprint 51 Feature 51.2: LLM Answer Streaming

        This method enables real-time token streaming for improved UX. Tokens are
        yielded as they're generated, allowing the frontend to display partial answers
        immediately.

        Args:
            query: User question
            contexts: Retrieved document contexts
            mode: "simple" or "multi_hop" reasoning mode

        Yields:
            dict: Token events with format:
                - {"event": "token", "data": {"content": "token_text"}}
                - {"event": "complete", "data": {"done": True}}
                - {"event": "error", "data": {"error": "error_message"}}

        Example:
            >>> async for event in generator.generate_streaming(
            ...     query="What is AEGIS?",
            ...     contexts=[{"text": "AEGIS is...", "source": "doc.md"}]
            ... ):
            ...     if event["event"] == "token":
            ...         print(event["data"]["content"], end="", flush=True)
        """
        import time

        if not contexts:
            # No context case - return full answer immediately
            answer = self._no_context_answer(query)
            yield {"event": "token", "data": {"content": answer}}
            yield {"event": "complete", "data": {"done": True}}
            return

        # Format contexts
        context_text = self._format_contexts(contexts)

        # Select prompt based on mode
        if mode == "multi_hop":
            prompt = MULTI_HOP_REASONING_PROMPT.format(contexts=context_text, query=query)
            complexity = Complexity.HIGH
        else:
            prompt = ANSWER_GENERATION_PROMPT.format(context=context_text, query=query)
            complexity = Complexity.MEDIUM

        logger.debug(
            "generating_answer_streaming",
            query=query[:100],
            contexts_count=len(contexts),
        )

        try:
            # Track TTFT (Time-To-First-Token)
            start_time = time.perf_counter()
            first_token_received = False
            ttft_ms = None
            accumulated_tokens = []

            # Create LLM task for streaming
            task = LLMTask(
                task_type=TaskType.GENERATION,
                prompt=prompt,
                quality_requirement=QualityRequirement.MEDIUM,
                complexity=complexity,
                temperature=self.temperature,
                model_local=self.model_name,
            )

            # Sprint 51: Use AegisLLMProxy streaming
            # The proxy's generate() method with stream=True returns an async generator
            async for chunk in self.proxy.generate_streaming(task):
                # Track TTFT on first token
                if not first_token_received:
                    ttft_ms = (time.perf_counter() - start_time) * 1000
                    first_token_received = True
                    logger.info(
                        "ttft_measured",
                        ttft_ms=ttft_ms,
                        query=query[:100],
                    )

                # Extract token content from chunk
                if isinstance(chunk, dict) and "content" in chunk:
                    token_content = chunk["content"]
                elif hasattr(chunk, "choices") and chunk.choices:
                    # ANY-LLM format: chunk.choices[0].delta.content
                    delta = chunk.choices[0].delta
                    token_content = getattr(delta, "content", "") if delta else ""
                else:
                    # Fallback: convert to string
                    token_content = str(chunk)

                # Only yield non-empty tokens
                if token_content:
                    accumulated_tokens.append(token_content)
                    yield {"event": "token", "data": {"content": token_content}}

            # Calculate total generation time
            total_time_ms = (time.perf_counter() - start_time) * 1000
            full_answer = "".join(accumulated_tokens)

            logger.info(
                "answer_streaming_complete",
                query=query[:100],
                answer_length=len(full_answer),
                contexts_used=len(contexts),
                ttft_ms=ttft_ms,
                total_time_ms=total_time_ms,
                tokens_streamed=len(accumulated_tokens),
            )

            # Yield completion event
            yield {"event": "complete", "data": {"done": True}}

        except Exception as e:
            logger.error(
                "answer_streaming_failed",
                query=query[:100],
                error=str(e),
            )
            # Yield error event
            yield {"event": "error", "data": {"error": str(e)}}

            # Fallback: yield fallback answer as a single token
            fallback = self._fallback_answer(query, contexts)
            yield {"event": "token", "data": {"content": fallback}}
            yield {"event": "complete", "data": {"done": True}}

    async def generate_with_citations_streaming(
        self,
        query: str,
        contexts: list[dict[str, Any]],
    ):
        """Stream LLM response token-by-token with citation support.

        Sprint 52: LLM Answer Streaming with Citations

        This method combines citation generation with real-time token streaming.
        It yields tokens as they're generated while maintaining citation mapping.

        Args:
            query: User question
            contexts: Retrieved document contexts

        Yields:
            dict: Token events with format:
                - {"event": "token", "data": {"content": "token_text"}}
                - {"event": "citation_map", "data": {...}}  # Sent before tokens
                - {"event": "complete", "data": {"done": True, "answer": "full_answer"}}
                - {"event": "error", "data": {"error": "error_message"}}
        """
        import time

        # Handle no contexts case
        if not contexts:
            answer = self._no_context_answer(query)
            yield {"event": "citation_map", "data": {}}
            yield {"event": "token", "data": {"content": answer}}
            yield {"event": "complete", "data": {"done": True, "answer": answer}}
            return

        # Limit to top 10 sources
        top_contexts = contexts[:10]

        # Build citation map FIRST and emit it
        citation_map = self._build_citation_map(top_contexts)
        yield {"event": "citation_map", "data": citation_map}

        # Format contexts with source IDs for prompt
        context_text = self._format_contexts_with_citations(top_contexts)

        # Build prompt for citation generation
        prompt = ANSWER_GENERATION_WITH_CITATIONS_PROMPT.format(contexts=context_text, query=query)

        logger.debug(
            "generating_answer_with_citations_streaming",
            query=query[:100],
            contexts_count=len(top_contexts),
        )

        try:
            # Track TTFT
            start_time = time.perf_counter()
            first_token_received = False
            ttft_ms = None
            accumulated_tokens = []

            # Create LLM task for streaming
            task = LLMTask(
                task_type=TaskType.GENERATION,
                prompt=prompt,
                quality_requirement=QualityRequirement.MEDIUM,
                complexity=Complexity.MEDIUM,
                temperature=self.temperature,
                model_local=self.model_name,
            )

            # Stream tokens from AegisLLMProxy
            async for chunk in self.proxy.generate_streaming(task):
                # Track TTFT on first token
                if not first_token_received:
                    ttft_ms = (time.perf_counter() - start_time) * 1000
                    first_token_received = True
                    logger.info(
                        "ttft_measured_with_citations",
                        ttft_ms=ttft_ms,
                        query=query[:100],
                    )

                # Extract token content from chunk
                if isinstance(chunk, dict) and "content" in chunk:
                    token_content = chunk["content"]
                elif hasattr(chunk, "choices") and chunk.choices:
                    delta = chunk.choices[0].delta
                    token_content = getattr(delta, "content", "") if delta else ""
                else:
                    token_content = str(chunk)

                # Only yield non-empty tokens
                if token_content:
                    accumulated_tokens.append(token_content)
                    yield {"event": "token", "data": {"content": token_content}}

            # Calculate total generation time
            total_time_ms = (time.perf_counter() - start_time) * 1000
            full_answer = "".join(accumulated_tokens)

            # Extract cited sources for logging
            cited_sources = self._extract_cited_sources(full_answer)

            logger.info(
                "answer_with_citations_streaming_complete",
                query=query[:100],
                answer_length=len(full_answer),
                contexts_used=len(top_contexts),
                citations_used=len(cited_sources),
                ttft_ms=ttft_ms,
                total_time_ms=total_time_ms,
            )

            # Yield completion event with full answer
            yield {
                "event": "complete",
                "data": {
                    "done": True,
                    "answer": full_answer,
                    "citation_map": citation_map,
                },
            }

        except Exception as e:
            logger.error(
                "answer_with_citations_streaming_failed",
                query=query[:100],
                error=str(e),
            )
            # Yield error and fallback
            yield {"event": "error", "data": {"error": str(e)}}
            fallback = self._fallback_answer(query, top_contexts)
            yield {"event": "token", "data": {"content": fallback}}
            yield {
                "event": "complete",
                "data": {"done": True, "answer": fallback, "citation_map": citation_map},
            }


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
