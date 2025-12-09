"""Follow-up Question Generator for conversational depth.

Sprint 27 Feature 27.5: Follow-up Question Suggestions

This module generates 3-5 follow-up questions after each answer to guide
users to deeper insights and increase engagement (Perplexity-style UX).

The generator:
1. Analyzes the Q&A context (query + answer + sources)
2. Uses fast LLM to generate related questions
3. Returns suggestions that explore related topics, clarify complex points,
   go deeper into details, or connect to broader context
"""

import json
from typing import Any

import structlog

from src.components.llm_proxy import get_aegis_llm_proxy
from src.components.llm_proxy.models import (
    Complexity,
    LLMTask,
    QualityRequirement,
    TaskType,
)
from src.core.exceptions import AegisRAGException

logger = structlog.get_logger(__name__)


async def generate_followup_questions(
    query: str,
    answer: str,
    sources: list[dict[str, Any]] | None = None,
    max_questions: int = 5,
) -> list[str]:
    """Generate 3-5 follow-up questions based on Q&A context.

    This function uses a fast local LLM to generate insightful follow-up
    questions that encourage users to explore related topics, clarify
    complex points, or dive deeper into the subject matter.

    Args:
        query: Original user query
        answer: Generated answer text
        sources: Optional list of source documents (dicts with 'text' field)
        max_questions: Maximum number of questions to return (default: 5)

    Returns:
        List of 3-5 follow-up question strings

    Raises:
        AegisRAGException: If LLM call fails critically

    Example:
        >>> questions = await generate_followup_questions(
        ...     query="What is AEGIS RAG?",
        ...     answer="AEGIS RAG is an agentic RAG system...",
        ...     sources=[{"text": "Vector search component..."}]
        ... )
        >>> print(questions)
        ["How does vector search work in AEGIS RAG?",
         "What are the key components of the system?",
         "How does it compare to traditional RAG?"]
    """
    try:
        # Build context from sources (first 3 for brevity to avoid token limits)
        source_context = ""
        if sources:
            source_snippets = []
            for src in sources[:3]:
                # Handle both dict and SourceDocument objects
                if isinstance(src, dict):
                    text = src.get("text", "")
                elif hasattr(src, "text"):
                    text = src.text
                else:
                    text = str(src)[:200]

                # Truncate to 200 chars
                if text:
                    source_snippets.append(f"- {text[:200]}...")

            if source_snippets:
                source_context = "\n".join(source_snippets)

        # Truncate query and answer to avoid excessive token usage
        query_short = query[:300]
        answer_short = answer[:500]

        # Construct prompt for follow-up generation
        prompt = f"""Based on this Q&A exchange, suggest 3-5 insightful follow-up questions.

Original Question: {query_short}

Answer: {answer_short}
"""

        if source_context:
            prompt += f"""
Available Context:
{source_context}
"""

        prompt += """
Generate questions that:
1. Explore related topics mentioned in the answer
2. Request clarification on complex points
3. Go deeper into specific details
4. Connect to broader context

Output ONLY a JSON array of question strings (no other text):
["question1", "question2", "question3"]
"""

        # Use AegisLLMProxy with fast local model
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt=prompt,
            quality_requirement=QualityRequirement.MEDIUM,  # Don't need critical quality
            complexity=Complexity.LOW,  # Simple task
            max_tokens=512,
            temperature=0.7,  # Some creativity for diverse questions
            model_local="qwen3:8b",  # Fast Qwen3 8B model (DGX Spark)
        )

        proxy = get_aegis_llm_proxy()
        result = await proxy.generate(task)

        # Parse JSON response
        content = result.content.strip()

        # Try to extract JSON if wrapped in markdown code blocks
        if content.startswith("```"):
            # Remove markdown code blocks
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        questions = json.loads(content)

        # Validate response format
        if not isinstance(questions, list):
            logger.warning(
                "followup_generation_invalid_format",
                content_type=type(questions).__name__,
                content=str(questions)[:100],
            )
            return []

        # Filter and validate questions
        valid_questions = []
        for q in questions:
            if isinstance(q, str) and len(q.strip()) >= 10:
                valid_questions.append(q.strip())

        # Limit to max_questions
        valid_questions = valid_questions[:max_questions]

        logger.info(
            "followup_questions_generated",
            count=len(valid_questions),
            query_preview=query[:50],
            provider=result.provider,
            cost_usd=result.cost_usd,
        )

        return valid_questions

    except json.JSONDecodeError as e:
        logger.warning(
            "followup_generation_json_parse_error",
            error=str(e),
            query=query[:50],
        )
        # Return empty list for non-critical errors
        return []

    except AegisRAGException as e:
        logger.error(
            "followup_generation_aegis_error",
            error=str(e),
            query=query[:50],
        )
        # Return empty list instead of raising (non-critical feature)
        return []

    except Exception as e:
        logger.error(
            "followup_generation_unexpected_error",
            error=str(e),
            query=query[:50],
            exc_info=True,
        )
        # Return empty list for any other errors
        return []


# Export public API
__all__ = [
    "generate_followup_questions",
]
