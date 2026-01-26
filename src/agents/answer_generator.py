"""LLM-based answer generation for RAG.

Sprint 11: Feature 11.1 - LLM-Based Answer Generation
Sprint 23: Feature 23.6 - AegisLLMProxy Integration
Sprint 27: Feature 27.10 - Inline Source Citations
Sprint 92: Feature 92.x - Context Relevance Threshold (anti-hallucination)
Migrated from Ollama to multi-cloud LLM proxy (Local → Alibaba Cloud → OpenAI).
"""

import re
from typing import Any

import structlog

from src.components.llm_proxy import get_aegis_llm_proxy

# Sprint 92: Context Relevance Threshold (anti-hallucination)
# If no retrieved context has a relevance score above this threshold,
# refuse to generate an answer to prevent hallucination.
# This value can be configured via Admin UI in Sprint 97.
MIN_CONTEXT_RELEVANCE_THRESHOLD = 0.3
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
    FAITHFULNESS_STRICT_PROMPT,
    FAITHFULNESS_STRICT_PROMPT_EN,
    MULTI_HOP_REASONING_PROMPT,
    NO_HEDGING_FAITHFULNESS_PROMPT,
    NO_HEDGING_FAITHFULNESS_PROMPT_EN,
    TOOL_AWARENESS_INSTRUCTION,
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

        Sprint 64 Feature 64.6: LLM model now respects Admin UI configuration

        Args:
            model_name: Explicit LLM model name (overrides Admin UI config)
            temperature: LLM temperature for answer generation (0.0 = deterministic)
        """
        # Store explicit model or None (fetch from Admin UI config on first use)
        self._explicit_model_name = model_name
        self.temperature = temperature

        # Sprint 23: Use AegisLLMProxy for multi-cloud routing
        self.proxy = get_aegis_llm_proxy()

        logger.info(
            "answer_generator_initialized",
            explicit_model=self._explicit_model_name,
            temperature=self.temperature,
            proxy="AegisLLMProxy",
        )

    async def _get_llm_model(
        self,
        query: str | None = None,
        intent: str | None = None,
    ) -> str:
        """Get LLM model from explicit config, model router, or Admin UI configuration.

        Sprint 64 Feature 64.6: LLM model respects Admin UI configuration
        Sprint 69 Feature 69.3: Model selection based on query complexity

        Returns the explicitly provided model if set, otherwise uses the model router
        to select an appropriate model based on query complexity, falling back to
        the centralized LLM config service if model selection is disabled.

        Args:
            query: User query (for complexity-based model selection)
            intent: Query intent (for complexity-based model selection)

        Returns:
            Model name (without provider prefix, e.g., "qwen3:32b" or "llama3.2:3b")

        Example:
            >>> generator = AnswerGenerator()  # No explicit model
            >>> # Simple query → fast model
            >>> model = await generator._get_llm_model("What is RAG?", "factual")
            >>> # Returns "llama3.2:3b" (fast tier)
            >>> # Complex query → advanced model
            >>> model = await generator._get_llm_model("Explain graph reasoning", "exploratory")
            >>> # Returns "qwen2.5:14b" (advanced tier)
        """
        if self._explicit_model_name:
            return self._explicit_model_name

        # Sprint 69 Feature 69.3: Use model router for complexity-based selection
        # Only if query and intent are provided
        if query and intent:
            try:
                from src.domains.llm_integration.model_router import get_model_router

                router = get_model_router()
                model_config = router.select_model(query, intent)

                logger.debug(
                    "using_model_router_selection",
                    model=model_config["model"],
                    tier=model_config["tier"],
                    complexity_score=model_config["complexity_score"],
                    expected_latency_ms=model_config["expected_latency_ms"],
                )

                return model_config["model"]

            except Exception as e:
                logger.warning(
                    "model_router_selection_failed",
                    error=str(e),
                    fallback="admin_ui_config",
                )
                # Fall through to Admin UI config

        # Fetch from Admin UI config
        from src.components.llm_config import LLMUseCase, get_llm_config_service

        config_service = get_llm_config_service()
        model = await config_service.get_model_for_use_case(LLMUseCase.ANSWER_GENERATION)

        logger.debug(
            "using_admin_ui_configured_model",
            model=model,
            use_case="answer_generation",
        )

        return model

    async def _get_relevance_threshold(self) -> float:
        """Get context relevance threshold from config service.

        Sprint 92: Anti-hallucination feature
        Sprint 97: UI configuration planned

        Returns:
            Relevance threshold (0.0-1.0), defaults to MIN_CONTEXT_RELEVANCE_THRESHOLD
        """
        try:
            from src.components.generation_config import get_generation_config_service

            config_service = get_generation_config_service()
            config = await config_service.get_config()
            return config.context_relevance_threshold
        except Exception as e:
            logger.debug(
                "relevance_threshold_fallback",
                error=str(e),
                using_default=MIN_CONTEXT_RELEVANCE_THRESHOLD,
            )
            return MIN_CONTEXT_RELEVANCE_THRESHOLD

    def _check_context_relevance(
        self,
        contexts: list[dict[str, Any]],
        threshold: float | None = None,
    ) -> tuple[bool, float]:
        """Check if any context has sufficient relevance to answer the query.

        Sprint 92: Anti-hallucination feature
        If no context exceeds the relevance threshold, we should refuse to generate
        an answer rather than risk hallucinating information from LLM training data.

        Args:
            contexts: Retrieved document contexts with 'score' or 'relevance' keys
            threshold: Minimum relevance score (default: MIN_CONTEXT_RELEVANCE_THRESHOLD)

        Returns:
            Tuple of (has_relevant_context, max_relevance_score)
            - has_relevant_context: True if at least one context exceeds threshold
            - max_relevance_score: Highest relevance score found (for logging)

        Example:
            >>> contexts = [{"text": "...", "score": 0.25}, {"text": "...", "score": 0.15}]
            >>> has_relevant, max_score = generator._check_context_relevance(contexts)
            >>> has_relevant
            False  # No context above 0.3 threshold
            >>> max_score
            0.25
        """
        if threshold is None:
            threshold = MIN_CONTEXT_RELEVANCE_THRESHOLD

        max_score = 0.0
        for ctx in contexts:
            # Try multiple score field names
            score = ctx.get("score") or ctx.get("relevance") or ctx.get("rerank_score") or 0.0
            if isinstance(score, (int, float)):
                max_score = max(max_score, float(score))

        has_relevant = max_score >= threshold

        logger.debug(
            "context_relevance_check",
            num_contexts=len(contexts),
            max_relevance=max_score,
            threshold=threshold,
            has_relevant_context=has_relevant,
        )

        return has_relevant, max_score

    def _no_relevant_context_answer(self, query: str, max_score: float) -> str:
        """Return a standardized response when no relevant contexts are found.

        Sprint 92: Anti-hallucination feature
        Instead of hallucinating, we explicitly inform the user that the
        information is not available in the knowledge base.

        Args:
            query: Original user query
            max_score: Highest relevance score found (for context)

        Returns:
            Standardized "not found" response in German
        """
        logger.warning(
            "no_relevant_context_for_query",
            query=query[:100],
            max_relevance_score=max_score,
            threshold=MIN_CONTEXT_RELEVANCE_THRESHOLD,
            action="refusing_to_generate",
        )

        return (
            "Zu dieser Frage sind keine relevanten Informationen in der Wissensdatenbank verfügbar. "
            "Bitte formulieren Sie Ihre Frage um oder fragen Sie nach einem anderen Thema."
        )

    async def generate_answer(
        self,
        query: str,
        contexts: list[dict[str, Any]],
        mode: str = "simple",
        intent: str | None = None,
    ) -> str:
        """Generate answer from query and retrieved contexts.

        Sprint 69 Feature 69.3: Added intent parameter for model selection

        Args:
            query: User question
            contexts: Retrieved document contexts (list of dicts with 'text' and 'source' keys)
            mode: "simple" or "multi_hop" reasoning mode
            intent: Query intent for complexity-based model selection (optional)

        Returns:
            Generated answer string
        """
        if not contexts:
            return self._no_context_answer(query)

        # Sprint 92: Check context relevance before generating
        # Prevents hallucination when contexts are irrelevant to the query
        # Load threshold from config service (allows UI configuration in Sprint 97)
        threshold = await self._get_relevance_threshold()
        has_relevant, max_score = self._check_context_relevance(contexts, threshold)
        if not has_relevant:
            return self._no_relevant_context_answer(query, max_score)

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
            # Sprint 69 Feature 69.3: Get model with complexity-based selection
            # Pass query and intent for model router
            model_name = await self._get_llm_model(query=query, intent=intent)

            # Sprint 23: Use AegisLLMProxy for generation
            task = LLMTask(
                task_type=TaskType.GENERATION,
                prompt=prompt,
                quality_requirement=QualityRequirement.MEDIUM,
                complexity=complexity,
                temperature=self.temperature,
                model_local=model_name,  # Uses model router or Admin UI config
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
                model=model_name,
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
        intent: str | None = None,
        strict_faithfulness: bool | None = None,
        no_hedging: bool = False,
    ) -> tuple[str, dict[int, dict[str, Any]]]:
        """Generate answer with inline source citations.

        Sprint 27 Feature 27.10: Inline Source Citations
        Sprint 69 Feature 69.3: Added intent parameter for model selection
        Sprint 80 Feature 80.1: Strict faithfulness mode for RAGAS optimization
        Sprint 81 Feature 81.8: No-hedging mode to eliminate meta-commentary
        TD-097: Load strict_faithfulness from Redis config if not explicitly passed

        Args:
            query: User question
            contexts: Retrieved document contexts (list of dicts with 'text', 'source', 'title', 'score', 'metadata')
            intent: Query intent for complexity-based model selection (optional)
            strict_faithfulness: When True, uses strict citation prompt that requires
                citations for EVERY sentence (no general knowledge allowed). This mode
                is designed to maximize RAGAS Faithfulness score.
                When None (default), loads value from Redis config (TD-097).
            no_hedging: When True, uses no-hedging prompt that forbids meta-commentary
                like "This information is not available". Eliminates LLM hedging behavior
                that causes Faithfulness penalties. Default: False. (Sprint 81 Feature 81.8)

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

        # Sprint 92: Check context relevance before generating
        # Prevents hallucination when contexts are irrelevant to the query
        # Load threshold from config service (allows UI configuration in Sprint 97)
        threshold = await self._get_relevance_threshold()
        has_relevant, max_score = self._check_context_relevance(contexts, threshold)
        if not has_relevant:
            return self._no_relevant_context_answer(query, max_score), {}

        # TD-097: Load strict_faithfulness from Redis config if not explicitly passed
        if strict_faithfulness is None:
            try:
                from src.components.generation_config import get_generation_config_service

                gen_config = await get_generation_config_service().get_config()
                strict_faithfulness = gen_config.strict_faithfulness_enabled
                logger.debug(
                    "generation_config_loaded",
                    strict_faithfulness=strict_faithfulness,
                )
            except Exception as e:
                # Fallback to False if config service fails
                logger.warning("generation_config_fallback", error=str(e))
                strict_faithfulness = False

        # Limit to top 10 sources (as per test requirements)
        top_contexts = contexts[:10]

        # Build citation map (always created, even if LLM fails)
        citation_map = self._build_citation_map(top_contexts)

        # Format contexts with source IDs for prompt
        context_text = self._format_contexts_with_citations(top_contexts)

        # Sprint 81 Feature 81.8: Select prompt based on no_hedging and strict_faithfulness modes
        # Priority: no_hedging > strict_faithfulness > standard_citations
        if no_hedging:
            # Sprint 81: No-hedging prompt forbids meta-commentary about document contents
            prompt = NO_HEDGING_FAITHFULNESS_PROMPT.format(contexts=context_text, query=query)
            prompt_mode = "no_hedging"
        elif strict_faithfulness:
            # Sprint 80: Strict mode requires citations for EVERY sentence (no general knowledge)
            prompt = FAITHFULNESS_STRICT_PROMPT.format(contexts=context_text, query=query)
            prompt_mode = "strict_faithfulness"
        else:
            prompt = ANSWER_GENERATION_WITH_CITATIONS_PROMPT.format(
                contexts=context_text, query=query
            )
            prompt_mode = "standard_citations"

        # Phase 1 Diagnostic Logging: Log full prompt for debugging
        logger.info(
            "CITATIONS_DEBUG_PROMPT",
            prompt_preview=prompt[:2000] if len(prompt) > 2000 else prompt,
            prompt_length=len(prompt),
            query=query,
            contexts_count=len(top_contexts),
            context_text_preview=context_text[:500] if len(context_text) > 500 else context_text,
            prompt_mode=prompt_mode,
            strict_faithfulness=strict_faithfulness,
            no_hedging=no_hedging,
        )

        try:
            # Sprint 69 Feature 69.3: Get model with complexity-based selection
            model_name = await self._get_llm_model(query=query, intent=intent)

            # Use AegisLLMProxy for generation
            task = LLMTask(
                task_type=TaskType.GENERATION,
                prompt=prompt,
                quality_requirement=QualityRequirement.MEDIUM,
                complexity=Complexity.MEDIUM,
                temperature=self.temperature,
                model_local=model_name,  # Uses Admin UI config (not hardcoded settings.*)
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
            # Sprint 64 Feature 64.6: Get model from Admin UI config (or explicit override)
            model_name = await self._get_llm_model()

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
                model_local=model_name,  # Uses Admin UI config (not hardcoded settings.*)
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
        intent: str | None = None,
        strict_faithfulness: bool | None = None,
        no_hedging: bool = False,
        tools_enabled: bool = False,
    ):
        """Stream LLM response token-by-token with citation support.

        Sprint 52: LLM Answer Streaming with Citations
        Sprint 69 Feature 69.3: Added intent parameter for model selection
        Sprint 80 Feature 80.1: Strict faithfulness mode for RAGAS optimization
        Sprint 81 Feature 81.8: No-hedging mode to eliminate meta-commentary
        Sprint 120 Feature 120.11: Tool-aware prompts for tool marker generation
        TD-097: Load strict_faithfulness from Redis config if not explicitly passed

        This method combines citation generation with real-time token streaming.
        It yields tokens as they're generated while maintaining citation mapping.

        Args:
            query: User question
            contexts: Retrieved document contexts
            intent: Query intent for complexity-based model selection (optional)
            strict_faithfulness: When True, uses strict citation prompt that requires
                citations for EVERY sentence (no general knowledge allowed). This mode
                is designed to maximize RAGAS Faithfulness score.
                When None (default), loads value from Redis config (TD-097).
            no_hedging: When True, uses no-hedging prompt that forbids meta-commentary
                like "This information is not available". Eliminates LLM hedging behavior
                that causes Faithfulness penalties. Default: False. (Sprint 81 Feature 81.8)
            tools_enabled: When True, injects tool-awareness instruction to teach LLM
                about tool markers ([TOOL:action], [SEARCH:query], [FETCH:url]).
                Default: False. (Sprint 120 Feature 120.11)

        Yields:
            dict: Token events with format:
                - {"event": "token", "data": {"content": "token_text"}}
                - {"event": "citation_map", "data": {...}}  # Sent before tokens
                - {"event": "complete", "data": {"done": True, "answer": "full_answer", "citation_map": {...}}}
                - {"event": "error", "data": {"error": "error_message"}}
        """
        import time

        # Handle no contexts case
        if not contexts:
            answer = self._no_context_answer(query)
            yield {"event": "citation_map", "data": {}}
            yield {"event": "token", "data": {"content": answer}}
            yield {
                "event": "complete",
                "data": {"done": True, "answer": answer, "citation_map": {}},
            }
            return

        # Sprint 92: Check context relevance before generating
        # Prevents hallucination when contexts are irrelevant to the query
        # Load threshold from config service (allows UI configuration in Sprint 97)
        threshold = await self._get_relevance_threshold()
        has_relevant, max_score = self._check_context_relevance(contexts, threshold)
        if not has_relevant:
            answer = self._no_relevant_context_answer(query, max_score)
            yield {"event": "citation_map", "data": {}}
            yield {"event": "token", "data": {"content": answer}}
            yield {
                "event": "complete",
                "data": {"done": True, "answer": answer, "citation_map": {}},
            }
            return

        # TD-097: Load strict_faithfulness from Redis config if not explicitly passed
        if strict_faithfulness is None:
            try:
                from src.components.generation_config import get_generation_config_service

                gen_config = await get_generation_config_service().get_config()
                strict_faithfulness = gen_config.strict_faithfulness_enabled
                logger.debug(
                    "generation_config_loaded_streaming",
                    strict_faithfulness=strict_faithfulness,
                )
            except Exception as e:
                # Fallback to False if config service fails
                logger.warning("generation_config_fallback_streaming", error=str(e))
                strict_faithfulness = False

        # Limit to top 10 sources
        top_contexts = contexts[:10]

        # Build citation map FIRST and emit it
        citation_map = self._build_citation_map(top_contexts)
        yield {"event": "citation_map", "data": citation_map}

        # Format contexts with source IDs for prompt
        context_text = self._format_contexts_with_citations(top_contexts)

        # Sprint 81 Feature 81.8: Select prompt based on no_hedging and strict_faithfulness modes
        # Priority: no_hedging > strict_faithfulness > standard_citations
        if no_hedging:
            # Sprint 81: No-hedging prompt forbids meta-commentary about document contents
            prompt = NO_HEDGING_FAITHFULNESS_PROMPT.format(contexts=context_text, query=query)
            prompt_mode = "no_hedging"
        elif strict_faithfulness:
            # Sprint 80: Strict mode requires citations for EVERY sentence (no general knowledge)
            prompt = FAITHFULNESS_STRICT_PROMPT.format(contexts=context_text, query=query)
            prompt_mode = "strict_faithfulness"
        else:
            prompt = ANSWER_GENERATION_WITH_CITATIONS_PROMPT.format(
                contexts=context_text, query=query
            )
            prompt_mode = "standard_citations"

        # Sprint 120 Feature 120.11: Inject tool-awareness instruction when tools enabled
        # This teaches the LLM to use tool markers ([TOOL:...], [SEARCH:...], [FETCH:...])
        # when the provided sources are insufficient to answer the query.
        if tools_enabled:
            # Insert tool instruction before "**Antwort:**" section
            # The instruction is in German to match the existing prompt language
            prompt = prompt.replace("**Antwort:**", f"{TOOL_AWARENESS_INSTRUCTION}\n**Antwort:**")
            prompt_mode = f"{prompt_mode}_with_tools"

        logger.debug(
            "generating_answer_with_citations_streaming",
            query=query[:100],
            contexts_count=len(top_contexts),
            prompt_mode=prompt_mode,
            strict_faithfulness=strict_faithfulness,
            no_hedging=no_hedging,
            tools_enabled=tools_enabled,
        )

        try:
            # Sprint 69 Feature 69.3: Get model with complexity-based selection
            model_name = await self._get_llm_model(query=query, intent=intent)

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
                model_local=model_name,  # Uses Admin UI config (not hardcoded settings.*)
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
