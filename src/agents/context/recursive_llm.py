"""Recursive LLM Module for processing large documents.

Sprint Context:
    - Sprint 92 (2026-01-14): Feature 92.1 - Recursive LLM Module (12 SP)

Process documents far exceeding context window through recursive exploration,
integrated with skill-based context management.

Based on: Zhang et al. (2025) "Recursive Language Models"
    arXiv:2512.24601 - Context as external environment

Architecture:
    Large Document (200 pages)
         │
         ▼
    ┌──────────────┐
    │  Segmenter   │ → Chapters/Sections (10-20 segments)
    │  (Skill)     │   Uses: recursive-context skill
    └──────────────┘
         │
         ▼
    ┌──────────────┐
    │ Relevance    │ → Score each segment (0.0-1.0)
    │ Scorer       │   Uses: relevance-scoring skill
    └──────────────┘
         │
         ▼
    ┌──────────────┐
    │ Recursive    │ → Dive into high-score segments
    │ Explorer     │ → Generate sub-queries
    └──────────────┘   Context Budget: 4000 tokens/dive
         │
         ▼
    ┌──────────────┐
    │ Aggregator   │ → Combine findings across levels
    │ (Skill)      │   Uses: synthesis skill
    └──────────────┘
         │
         ▼
    Final Answer (with hierarchical citations)

Example:
    >>> from src.agents.context.recursive_llm import RecursiveLLMProcessor
    >>> from src.agents.skills import get_skill_registry
    >>> from langchain_ollama import ChatOllama
    >>>
    >>> llm = ChatOllama(model="llama3.2:8b")
    >>> processor = RecursiveLLMProcessor(
    ...     llm=llm,
    ...     skill_registry=get_skill_registry()
    ... )
    >>>
    >>> result = await processor.process(
    ...     document=large_document,
    ...     query="What are the main research findings?"
    ... )
    >>> print(result["answer"])
    >>> print(f"Processed {result['segments_processed']} segments")
    >>> print(f"Max depth: {result['max_depth_reached']}")

Notes:
    - Processes documents 10x+ longer than context window
    - Uses skill-provided prompts for relevance scoring
    - Recursive depth configurable (default: 3 levels)
    - Natural breakpoints preferred (paragraphs, sections)
    - Overlapping segments prevent information loss

See Also:
    - docs/sprints/SPRINT_92_PLAN.md: Feature specification
    - src/agents/skills/registry.py: Skill system integration
    - arXiv:2512.24601: Research paper on Recursive LLM
"""

from dataclasses import dataclass
from typing import Any, Optional

import structlog
from langchain_core.language_models.chat_models import BaseChatModel

from src.agents.skills.registry import LoadedSkill, SkillRegistry

logger = structlog.get_logger(__name__)


@dataclass
class DocumentSegment:
    """Segment of a large document.

    Attributes:
        id: Unique segment identifier (e.g., "seg_0_1")
        content: Text content of the segment
        level: Depth in hierarchy (0 = top level, 1 = first recursion, etc.)
        parent_id: ID of parent segment (None for top-level)
        start_offset: Character offset in original document
        end_offset: Character offset in original document
        relevance_score: Relevance to query (0.0-1.0)
        summary: LLM-generated summary of segment

    Example:
        >>> segment = DocumentSegment(
        ...     id="seg_0_1",
        ...     content="Chapter 1: Introduction...",
        ...     level=0,
        ...     parent_id=None,
        ...     start_offset=0,
        ...     end_offset=5000,
        ...     relevance_score=0.85,
        ...     summary="Introduces main research question..."
        ... )
    """

    id: str
    content: str
    level: int
    parent_id: Optional[str]
    start_offset: int
    end_offset: int
    relevance_score: float = 0.0
    summary: str = ""


class RecursiveLLMProcessor:
    """Process large documents recursively with skill integration.

    Based on: Zhang et al. (2025) "Recursive Language Models"
        arXiv:2512.24601

    This processor treats large documents as external environments that can be
    explored programmatically. It recursively segments, scores, and explores
    relevant document sections to extract information for answering queries.

    Attributes:
        llm: Language model for scoring and summarization
        skills: Skill registry for loading context skills
        context_window: Maximum tokens per segment (default: 8192)
        overlap_tokens: Overlap between segments (default: 200)
        max_depth: Maximum recursion depth (default: 3)
        relevance_threshold: Minimum score for exploration (default: 0.5)

    Example:
        >>> from langchain_ollama import ChatOllama
        >>> from src.agents.skills import get_skill_registry
        >>>
        >>> llm = ChatOllama(model="llama3.2:8b")
        >>> processor = RecursiveLLMProcessor(
        ...     llm=llm,
        ...     skill_registry=get_skill_registry(),
        ...     context_window=8192,
        ...     max_depth=3
        ... )
        >>>
        >>> result = await processor.process(
        ...     document=long_doc,
        ...     query="Summarize the methodology"
        ... )
    """

    def __init__(
        self,
        llm: BaseChatModel,
        skill_registry: SkillRegistry,
        context_window: int = 8192,
        overlap_tokens: int = 200,
        max_depth: int = 3,
        relevance_threshold: float = 0.5,
    ):
        """Initialize recursive LLM processor.

        Args:
            llm: Language model for scoring and summarization
            skill_registry: Skill registry for loading context skills
            context_window: Maximum tokens per segment (default: 8192)
            overlap_tokens: Overlap between segments in tokens (default: 200)
            max_depth: Maximum recursion depth (default: 3)
            relevance_threshold: Minimum relevance score for exploration (0.0-1.0)
        """
        self.llm = llm
        self.skills = skill_registry
        self.context_window = context_window
        self.overlap_tokens = overlap_tokens
        self.max_depth = max_depth
        self.relevance_threshold = relevance_threshold

        logger.info(
            "recursive_llm_processor_initialized",
            context_window=context_window,
            overlap_tokens=overlap_tokens,
            max_depth=max_depth,
            relevance_threshold=relevance_threshold,
        )

    async def process(
        self,
        document: str,
        query: str,
        skill_context: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Recursively process large document with skill support.

        Args:
            document: Full document text
            query: User's question to answer
            skill_context: Optional skill execution context

        Returns:
            Dict containing:
                - answer: Final answer synthesized from findings
                - segments_processed: Number of segments explored
                - max_depth_reached: Maximum recursion depth reached
                - total_segments: Total segments created
                - skills_used: List of skills activated

        Raises:
            ValueError: If document is empty or query is invalid

        Example:
            >>> result = await processor.process(
            ...     document=large_document,
            ...     query="What are the main conclusions?"
            ... )
            >>> print(result["answer"])
            >>> print(f"Explored {result['segments_processed']} segments")
        """
        if not document or not document.strip():
            raise ValueError("Document cannot be empty")
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        logger.info(
            "recursive_processing_started",
            document_length=len(document),
            query=query[:100],
        )

        # Activate recursive-context skill
        recursive_skill = None
        try:
            # Load skill if available (graceful degradation if not found)
            if "recursive-context" in self.skills.list_available():
                self.skills.activate("recursive-context")
                recursive_skill = self.skills._loaded.get("recursive-context")
                logger.info("recursive_context_skill_activated")
            else:
                logger.warning(
                    "recursive_context_skill_not_found",
                    message="Proceeding without skill guidance",
                )
        except Exception as e:
            logger.warning(
                "recursive_context_skill_activation_failed",
                error=str(e),
                message="Proceeding without skill",
            )

        # Step 1: Segment document
        segments = self._segment_document(document, level=0)
        logger.info("document_segmented", segment_count=len(segments))

        # Step 2: Score relevance using skill
        scored_segments = await self._score_relevance(segments, query, recursive_skill)
        logger.info(
            "segments_scored",
            avg_score=sum(s.relevance_score for s in scored_segments) / len(scored_segments)
            if scored_segments
            else 0.0,
        )

        # Step 3: Recursive exploration
        findings = []
        for segment in scored_segments:
            if segment.relevance_score >= self.relevance_threshold:
                finding = await self._explore_segment(segment, query, depth=1, skill=recursive_skill)
                findings.append(finding)
                logger.debug(
                    "segment_explored",
                    segment_id=segment.id,
                    relevance=segment.relevance_score,
                )

        logger.info("exploration_complete", findings_count=len(findings))

        # Step 4: Aggregate findings using synthesis skill
        synthesis_skill = None
        try:
            if "synthesis" in self.skills.list_available():
                self.skills.activate("synthesis")
                synthesis_skill = self.skills._loaded.get("synthesis")
                logger.info("synthesis_skill_activated")
        except Exception as e:
            logger.warning("synthesis_skill_activation_failed", error=str(e))

        answer = await self._aggregate_findings(findings, query, synthesis_skill)

        # Unload skills to free context budget
        if recursive_skill:
            self.skills.deactivate("recursive-context")
        if synthesis_skill:
            self.skills.deactivate("synthesis")

        result = {
            "answer": answer,
            "segments_processed": len(findings),
            "max_depth_reached": max((f.get("depth", 0) for f in findings), default=0),
            "total_segments": len(segments),
            "skills_used": [
                s for s in ["recursive-context", "synthesis"] if s in self.skills.list_active()
            ],
        }

        logger.info(
            "recursive_processing_complete",
            segments_processed=result["segments_processed"],
            max_depth=result["max_depth_reached"],
        )

        return result

    def _segment_document(
        self,
        text: str,
        level: int,
        parent_id: Optional[str] = None,
    ) -> list[DocumentSegment]:
        """Segment document into context-fitting chunks.

        Uses structural markers (headers, paragraphs) when possible.
        Ensures segments fit within context window with overlap.

        Args:
            text: Text to segment
            level: Depth in hierarchy
            parent_id: ID of parent segment (None for top-level)

        Returns:
            List of DocumentSegment objects

        Example:
            >>> segments = processor._segment_document(
            ...     text=long_text,
            ...     level=0
            ... )
            >>> len(segments)
            15
        """
        # Estimate tokens (rough: 4 chars = 1 token)
        chars_per_segment = (self.context_window - 500) * 4  # Leave room for prompt

        segments = []
        offset = 0
        segment_id = 0

        while offset < len(text):
            # Find natural break point
            end = min(offset + chars_per_segment, len(text))

            # Try to find paragraph break
            if end < len(text):
                para_break = text.rfind("\n\n", offset, end)
                if para_break > offset + chars_per_segment // 2:
                    end = para_break
                else:
                    # Try single newline
                    newline_break = text.rfind("\n", offset, end)
                    if newline_break > offset + chars_per_segment // 2:
                        end = newline_break

            segment_text = text[offset:end].strip()
            if segment_text:
                segments.append(
                    DocumentSegment(
                        id=f"seg_{level}_{segment_id}",
                        content=segment_text,
                        level=level,
                        parent_id=parent_id,
                        start_offset=offset,
                        end_offset=end,
                    )
                )
                segment_id += 1

            # Overlap to prevent information loss
            offset = end - (self.overlap_tokens * 4)

        logger.debug(
            "document_segmented",
            level=level,
            segment_count=len(segments),
            parent_id=parent_id,
        )

        return segments

    async def _score_relevance(
        self,
        segments: list[DocumentSegment],
        query: str,
        skill: Optional[LoadedSkill],
    ) -> list[DocumentSegment]:
        """Score each segment's relevance to query using skill instructions.

        Args:
            segments: List of document segments
            query: User's query
            skill: Loaded skill with scoring prompts (optional)

        Returns:
            List of segments sorted by relevance (highest first)

        Example:
            >>> scored = await processor._score_relevance(
            ...     segments=segments,
            ...     query="What is the main conclusion?",
            ...     skill=recursive_skill
            ... )
            >>> scored[0].relevance_score
            0.92
        """
        for segment in segments:
            preview = segment.content[:2000]  # Use first 2000 chars

            # Use skill-provided prompt template if available
            if skill and hasattr(skill, "prompts") and "relevance_scoring" in skill.prompts:
                prompt = skill.prompts["relevance_scoring"].format(
                    query=query,
                    text_preview=preview,
                )
            else:
                # Fallback prompt
                prompt = f"""Score the relevance of this text to the query on a scale of 0.0 to 1.0.

Query: {query}

Text Preview:
{preview}

Respond with ONLY a number between 0.0 and 1.0, where:
- 0.0 = completely irrelevant
- 0.5 = somewhat relevant
- 1.0 = highly relevant

Score:"""

            try:
                response = await self.llm.ainvoke(prompt)
                score_text = response.content.strip()
                # Extract first number found
                import re

                numbers = re.findall(r"0?\.\d+|[01]\.0", score_text)
                if numbers:
                    score = float(numbers[0])
                    segment.relevance_score = min(1.0, max(0.0, score))
                else:
                    segment.relevance_score = 0.5
                    logger.warning(
                        "relevance_score_parsing_failed",
                        segment_id=segment.id,
                        response=score_text[:100],
                    )
            except Exception as e:
                logger.error(
                    "relevance_scoring_error",
                    segment_id=segment.id,
                    error=str(e),
                )
                segment.relevance_score = 0.5

        segments.sort(key=lambda s: s.relevance_score, reverse=True)
        return segments

    async def _explore_segment(
        self,
        segment: DocumentSegment,
        query: str,
        depth: int,
        skill: Optional[LoadedSkill],
    ) -> dict[str, Any]:
        """Recursively explore a segment with skill support.

        Args:
            segment: Document segment to explore
            query: User's query
            depth: Current recursion depth
            skill: Loaded skill with summarization prompts (optional)

        Returns:
            Dict containing segment summary and sub-findings

        Example:
            >>> finding = await processor._explore_segment(
            ...     segment=high_score_segment,
            ...     query="What are the results?",
            ...     depth=1,
            ...     skill=recursive_skill
            ... )
            >>> print(finding["summary"])
        """
        # Use skill-provided summarization prompt if available
        if skill and hasattr(skill, "prompts") and "segment_summary" in skill.prompts:
            summary_prompt = skill.prompts["segment_summary"].format(
                query=query,
                content=segment.content,
            )
        else:
            # Fallback prompt
            summary_prompt = f"""Summarize the following text in relation to this query:

Query: {query}

Text:
{segment.content}

Summary:"""

        try:
            summary_response = await self.llm.ainvoke(summary_prompt)
            segment.summary = summary_response.content.strip()
        except Exception as e:
            logger.error(
                "segment_summarization_error",
                segment_id=segment.id,
                error=str(e),
            )
            segment.summary = f"[Error summarizing segment: {str(e)}]"

        result = {
            "segment_id": segment.id,
            "summary": segment.summary,
            "relevance": segment.relevance_score,
            "depth": depth,
            "sub_findings": [],
        }

        # Recursive dive if depth allows and segment is large enough
        if depth < self.max_depth and len(segment.content) > self.context_window * 2:
            sub_segments = self._segment_document(
                segment.content,
                level=depth,
                parent_id=segment.id,
            )

            if len(sub_segments) > 1:  # Only recurse if we can subdivide
                scored_subs = await self._score_relevance(sub_segments, query, skill)
                # Explore top 3 most relevant sub-segments
                for sub in scored_subs[:3]:
                    if sub.relevance_score >= self.relevance_threshold:
                        sub_finding = await self._explore_segment(sub, query, depth + 1, skill)
                        result["sub_findings"].append(sub_finding)

        return result

    async def _aggregate_findings(
        self,
        findings: list[dict[str, Any]],
        query: str,
        synthesis_skill: Optional[LoadedSkill],
    ) -> str:
        """Aggregate findings into final answer using synthesis skill.

        Args:
            findings: List of exploration findings
            query: User's query
            synthesis_skill: Loaded synthesis skill (optional)

        Returns:
            Final aggregated answer

        Example:
            >>> answer = await processor._aggregate_findings(
            ...     findings=all_findings,
            ...     query="What are the main results?",
            ...     synthesis_skill=synthesis_skill
            ... )
            >>> print(answer)
        """
        if not findings:
            return "No relevant information found in the document."

        # Build hierarchical summary
        all_summaries = []
        for finding in findings:
            all_summaries.append(f"[{finding['segment_id']}] {finding['summary']}")
            for sub in finding.get("sub_findings", []):
                all_summaries.append(f"  [{sub['segment_id']}] {sub['summary']}")
                # Include third level if present
                for subsub in sub.get("sub_findings", []):
                    all_summaries.append(f"    [{subsub['segment_id']}] {subsub['summary']}")

        combined = "\n\n".join(all_summaries)

        # Use synthesis skill prompt if available
        if (
            synthesis_skill
            and hasattr(synthesis_skill, "prompts")
            and "aggregate" in synthesis_skill.prompts
        ):
            prompt = synthesis_skill.prompts["aggregate"].format(
                query=query,
                findings=combined,
            )
        else:
            # Fallback prompt
            prompt = f"""Based on the following findings from different parts of a document, provide a comprehensive answer to the query.

Query: {query}

Findings:
{combined}

Synthesize these findings into a clear, coherent answer:"""

        try:
            response = await self.llm.ainvoke(prompt)
            return response.content.strip()
        except Exception as e:
            logger.error("aggregation_error", error=str(e))
            return f"Error aggregating findings: {str(e)}\n\nRaw findings:\n{combined}"
