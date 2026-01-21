"""Reflection skill for self-critique and validation.

Sprint Context:
    - Sprint 90 (2026-01-14): Feature 90.2 - Reflection Loop in Agent Core (8 SP)

Implements a Reflection Loop that allows the agent to self-critique and validate responses.

Based on: Reflexion paper (Shinn et al. 2023)
  - https://arxiv.org/abs/2303.11366

Process:
    1. Generate initial answer from contexts
    2. Critique answer for accuracy, completeness, hallucination
    3. Score confidence (0.0-1.0)
    4. Improve if score < threshold (max iterations)
    5. Return best answer with reflection trace

This would be packaged as: skills/reflection/

Example:
    >>> from src.agents.skills.reflection import ReflectionSkill
    >>> from src.components.llm_proxy import get_aegis_llm_proxy
    >>>
    >>> llm = get_aegis_llm_proxy()
    >>> skill = ReflectionSkill(llm)
    >>>
    >>> # Reflect on an answer
    >>> result = await skill.reflect(
    ...     query="What is photosynthesis?",
    ...     answer="Plants make food from sunlight.",
    ...     contexts=["Photosynthesis is the process..."]
    ... )
    >>> result.score
    0.65
    >>>
    >>> # Full reflection loop with improvements
    >>> result = await skill.reflect_and_improve(
    ...     query="What is photosynthesis?",
    ...     answer="Plants make food from sunlight.",
    ...     contexts=["Photosynthesis is the process..."]
    ... )
    >>> result.score
    0.92

Notes:
    - Max 3 iterations (configurable)
    - Confidence threshold: 0.85 (configurable)
    - Uses LLM for critique and improvement
    - Returns trace of all iterations

See Also:
    - docs/sprints/SPRINT_90_PLAN.md: Implementation details
    - src/agents/skills/registry.py: Skill registry system
"""

import re
from dataclasses import dataclass
from typing import List, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ReflectionResult:
    """Result of reflection step.

    Attributes:
        original_answer: Original answer before improvements
        critique: LLM critique of the answer
        score: Confidence score (0.0-1.0)
        issues: List of identified issues
        improved_answer: Improved answer (if improved)
        iteration: Iteration number (0 = initial)

    Example:
        >>> result = ReflectionResult(
        ...     original_answer="Plants make food.",
        ...     critique="SCORE: 0.65\\nISSUES: [incomplete, lacks detail]",
        ...     score=0.65,
        ...     issues=["incomplete", "lacks detail"],
        ...     improved_answer="Plants use photosynthesis...",
        ...     iteration=1
        ... )
    """

    original_answer: str
    critique: str
    score: float  # 0.0 - 1.0
    issues: List[str]
    improved_answer: Optional[str] = None
    iteration: int = 0


class ReflectionSkill:
    """Reflection skill for self-critique and validation.

    Loaded as: skills/reflection/

    Based on: Reflexion paper (Shinn et al. 2023)

    Attributes:
        llm: Language model for critique and improvement
        max_iterations: Maximum improvement iterations (default: 3)
        confidence_threshold: Minimum confidence score to stop (default: 0.85)

    Example:
        >>> from src.agents.skills.reflection import ReflectionSkill
        >>> from src.components.llm_proxy import get_aegis_llm_proxy
        >>>
        >>> llm = get_aegis_llm_proxy()
        >>> skill = ReflectionSkill(llm, max_iterations=3, confidence_threshold=0.85)
        >>>
        >>> result = await skill.reflect_and_improve(
        ...     query="What causes rain?",
        ...     answer="Water evaporates and falls as rain.",
        ...     contexts=["The water cycle involves..."]
        ... )
    """

    def __init__(
        self,
        llm,  # BaseChatModel or AegisLLMProxy
        max_iterations: int = 3,
        confidence_threshold: float = 0.85,
    ):
        """Initialize reflection skill.

        Args:
            llm: Language model for critique and improvement
            max_iterations: Maximum improvement iterations (default: 3)
            confidence_threshold: Minimum confidence score to stop (default: 0.85)
        """
        self.llm = llm
        self.max_iterations = max_iterations
        self.confidence_threshold = confidence_threshold

    async def reflect(self, query: str, answer: str, contexts: List[str]) -> ReflectionResult:
        """Reflect on an answer and identify issues.

        Steps:
        1. Critique the answer for factual accuracy
        2. Check alignment with provided contexts
        3. Identify missing information
        4. Score confidence

        Args:
            query: Original question
            answer: Answer to evaluate
            contexts: Retrieved contexts

        Returns:
            ReflectionResult with critique and score

        Example:
            >>> result = await skill.reflect(
            ...     query="What is mitosis?",
            ...     answer="Cell division.",
            ...     contexts=["Mitosis is a type of cell division..."]
            ... )
            >>> result.score
            0.6
            >>> result.issues
            ['incomplete', 'lacks steps']
        """
        critique_prompt = f"""You are a critical reviewer. Evaluate this answer:

Question: {query}

Contexts provided:
{self._format_contexts(contexts)}

Answer to evaluate:
{answer}

Evaluate for:
1. FACTUAL ACCURACY: Does it match the contexts?
2. COMPLETENESS: Does it fully answer the question?
3. HALLUCINATION: Does it include unsupported claims?
4. CLARITY: Is it clear and well-structured?

Provide:
SCORE: [0.0-1.0]
ISSUES: [list specific problems]
SUGGESTIONS: [improvements needed]

Critique:"""

        logger.debug("reflection_critique_start", query_length=len(query))

        # Invoke LLM
        response = await self.llm.ainvoke(critique_prompt)

        # Handle different response types (LangChain vs AegisLLMProxy)
        if hasattr(response, "content"):
            critique = response.content
        elif isinstance(response, dict):
            critique = response.get("content", str(response))
        else:
            critique = str(response)

        score = self._parse_score(critique)
        issues = self._parse_issues(critique)

        logger.info(
            "reflection_critique_complete",
            score=score,
            num_issues=len(issues),
            issues=issues,
        )

        return ReflectionResult(
            original_answer=answer,
            critique=critique,
            score=score,
            issues=issues,
            iteration=0,
        )

    async def improve(
        self, query: str, reflection: ReflectionResult, contexts: List[str]
    ) -> ReflectionResult:
        """Improve answer based on reflection.

        Args:
            query: Original question
            reflection: Previous reflection result
            contexts: Retrieved contexts

        Returns:
            New ReflectionResult with improved answer

        Example:
            >>> result = await skill.reflect(query, answer, contexts)
            >>> improved = await skill.improve(query, result, contexts)
            >>> improved.score > result.score
            True
        """
        if reflection.score >= self.confidence_threshold:
            logger.debug("reflection_already_confident", score=reflection.score)
            return reflection

        improve_prompt = f"""Improve this answer based on the critique.

Question: {query}

Contexts:
{self._format_contexts(contexts)}

Original Answer:
{reflection.original_answer}

Critique:
{reflection.critique}

Issues to fix:
{chr(10).join(f'- {issue}' for issue in reflection.issues)}

Write an improved answer that addresses all issues.
Only use information from the provided contexts.

Improved Answer:"""

        logger.debug("reflection_improve_start", iteration=reflection.iteration + 1)

        # Invoke LLM
        response = await self.llm.ainvoke(improve_prompt)

        # Handle different response types
        if hasattr(response, "content"):
            improved = response.content
        elif isinstance(response, dict):
            improved = response.get("content", str(response))
        else:
            improved = str(response)

        # Re-evaluate
        new_reflection = await self.reflect(query, improved, contexts)
        new_reflection.iteration = reflection.iteration + 1
        new_reflection.improved_answer = improved

        logger.info(
            "reflection_improve_complete",
            iteration=new_reflection.iteration,
            old_score=reflection.score,
            new_score=new_reflection.score,
            improvement=new_reflection.score - reflection.score,
        )

        return new_reflection

    async def reflect_and_improve(
        self, query: str, answer: str, contexts: List[str]
    ) -> ReflectionResult:
        """Full reflection loop with improvements.

        Iteratively improves answer until confidence threshold reached
        or max iterations exhausted.

        Args:
            query: Original question
            answer: Initial answer to improve
            contexts: Retrieved contexts

        Returns:
            Final ReflectionResult with best answer

        Example:
            >>> result = await skill.reflect_and_improve(
            ...     query="What is DNA?",
            ...     answer="Genetic material.",
            ...     contexts=["DNA is deoxyribonucleic acid..."]
            ... )
            >>> result.score
            0.92
            >>> result.iteration
            2
        """
        logger.info(
            "reflection_loop_start",
            max_iterations=self.max_iterations,
            threshold=self.confidence_threshold,
        )

        reflection = await self.reflect(query, answer, contexts)

        for i in range(self.max_iterations):
            if reflection.score >= self.confidence_threshold:
                logger.info(
                    "reflection_loop_complete",
                    reason="threshold_reached",
                    final_score=reflection.score,
                    iterations=reflection.iteration,
                )
                break
            reflection = await self.improve(query, reflection, contexts)
        else:
            logger.info(
                "reflection_loop_complete",
                reason="max_iterations",
                final_score=reflection.score,
                iterations=reflection.iteration,
            )

        return reflection

    def _format_contexts(self, contexts: List[str]) -> str:
        """Format contexts with numbered list.

        Args:
            contexts: List of context strings

        Returns:
            Formatted contexts string
        """
        return "\n\n".join(f"[{i+1}] {ctx}" for i, ctx in enumerate(contexts))

    def _parse_score(self, critique: str) -> float:
        """Parse confidence score from critique.

        Args:
            critique: LLM critique text

        Returns:
            Parsed score (0.0-1.0), defaults to 0.5 if not found
        """
        match = re.search(r"SCORE:\s*([0-9.]+)", critique)
        if match:
            score = float(match.group(1))
            return min(1.0, max(0.0, score))
        return 0.5

    def _parse_issues(self, critique: str) -> List[str]:
        """Parse issues list from critique.

        Args:
            critique: LLM critique text

        Returns:
            List of issues, empty if not found
        """
        issues = []
        match = re.search(r"ISSUES:\s*\[(.*?)\]", critique, re.DOTALL)
        if match:
            issues_text = match.group(1)
            issues = [i.strip() for i in issues_text.split(",") if i.strip()]
        return issues
