"""Follow-up Question Generator for conversational depth.

Sprint 27 Feature 27.5: Follow-up Question Suggestions
Sprint 52 Feature 52.3: Async Follow-up Questions (TD-043)
Sprint 113 Fix: Robust JSON array extraction (handle LLM extra text)

This module generates 3-5 follow-up questions after each answer to guide
users to deeper insights and increase engagement (Perplexity-style UX).

The generator:
1. Analyzes the Q&A context (query + answer + sources)
2. Uses fast LLM to generate related questions
3. Returns suggestions that explore related topics, clarify complex points,
   go deeper into details, or connect to broader context
4. (Sprint 52.3) Stores conversation context in Redis (TTL: 30 min)
5. (Sprint 52.3) Runs asynchronously without blocking answer display
"""

import json
from datetime import UTC, datetime
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

# Sprint 52 Feature 52.3: Context TTL (30 minutes)
FOLLOWUP_CONTEXT_TTL_SECONDS = 1800


async def store_conversation_context(
    session_id: str,
    query: str,
    answer: str,
    sources: list[dict[str, Any]] | None = None,
) -> bool:
    """Store conversation context in Redis for async follow-up generation.

    Sprint 52 Feature 52.3: Async Follow-up Questions (TD-043)

    This function stores the Q&A context in Redis with a 30-minute TTL,
    allowing follow-up questions to be generated asynchronously without
    blocking the answer display.

    Args:
        session_id: Session ID for this conversation
        query: Original user query
        answer: Generated answer text
        sources: Optional list of source documents

    Returns:
        True if storage succeeded, False otherwise

    Example:
        >>> success = await store_conversation_context(
        ...     session_id="session-123",
        ...     query="What is AEGIS RAG?",
        ...     answer="AEGIS RAG is an agentic RAG system...",
        ...     sources=[{"text": "Vector search component..."}]
        ... )
    """
    try:
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()

        # Build context data
        context_data = {
            "query": query,
            "answer": answer,
            "sources": sources or [],
            "stored_at": datetime.now(UTC).isoformat(),
        }

        # Store in Redis with 30-minute TTL
        cache_key = f"{session_id}:followup_context"
        success = await redis_memory.store(
            key=cache_key,
            value=context_data,
            namespace="cache",
            ttl_seconds=FOLLOWUP_CONTEXT_TTL_SECONDS,
        )

        if success:
            logger.info(
                "followup_context_stored",
                session_id=session_id,
                query_preview=query[:50],
            )
        else:
            logger.warning(
                "followup_context_storage_failed",
                session_id=session_id,
            )

        return success

    except Exception as e:
        logger.error(
            "followup_context_storage_error",
            session_id=session_id,
            error=str(e),
        )
        return False


async def retrieve_conversation_context(session_id: str) -> dict[str, Any] | None:
    """Retrieve conversation context from Redis for follow-up generation.

    Sprint 52 Feature 52.3: Async Follow-up Questions (TD-043)

    Args:
        session_id: Session ID for this conversation

    Returns:
        Context data if found, None otherwise
    """
    try:
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()

        cache_key = f"{session_id}:followup_context"
        context = await redis_memory.retrieve(key=cache_key, namespace="cache")

        if context:
            # Extract value from Redis wrapper
            if isinstance(context, dict) and "value" in context:
                context = context["value"]

            logger.info(
                "followup_context_retrieved",
                session_id=session_id,
            )
            return context

        logger.debug(
            "followup_context_not_found",
            session_id=session_id,
        )
        return None

    except Exception as e:
        logger.error(
            "followup_context_retrieval_error",
            session_id=session_id,
            error=str(e),
        )
        return None


async def generate_followup_questions(
    query: str,
    answer: str,
    sources: list[dict[str, Any]] | None = None,
    max_questions: int = 5,
) -> list[str]:
    """Generate 3-5 follow-up questions based on Q&A context.

    Sprint 27 Feature 27.5: Follow-up Question Suggestions
    Sprint 52 Feature 52.3: Async Follow-up Questions (TD-043)

    This function uses a fast local LLM to generate insightful follow-up
    questions that encourage users to explore related topics, clarify
    complex points, or dive deeper into the subject matter.

    CRITICAL: This should be called AFTER the answer is complete and
    should NOT block the answer display. For streaming responses, use
    generate_followup_questions_async() instead.

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
            model_local="nemotron-3-nano",  # Sprint 51: Fast Nemotron 3 Nano on DGX Spark
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

        # Sprint 113 Fix: Extract JSON array even if LLM adds extra text
        # The LLM sometimes adds explanatory text after the JSON array
        # Find the JSON array by bracket matching
        start_idx = content.find('[')
        if start_idx != -1:
            # Find matching closing bracket (handles nested arrays)
            bracket_count = 0
            end_idx = start_idx
            for i, char in enumerate(content[start_idx:], start_idx):
                if char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_idx = i + 1
                        break
            content = content[start_idx:end_idx]

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


async def generate_followup_questions_async(session_id: str) -> list[str]:
    """Generate follow-up questions asynchronously using stored context.

    Sprint 52 Feature 52.3: Async Follow-up Questions (TD-043)

    This function retrieves the conversation context from Redis and
    generates follow-up questions without blocking. It should be called
    as a background task AFTER the answer is fully streamed.

    Args:
        session_id: Session ID for this conversation

    Returns:
        List of 3-5 follow-up question strings, empty list if context not found

    Example:
        >>> # After answer is complete, trigger background task:
        >>> questions = await generate_followup_questions_async("session-123")
    """
    try:
        # Retrieve stored context
        context = await retrieve_conversation_context(session_id)

        if not context:
            logger.warning(
                "followup_async_no_context",
                session_id=session_id,
            )
            return []

        # Generate questions from context
        questions = await generate_followup_questions(
            query=context.get("query", ""),
            answer=context.get("answer", ""),
            sources=context.get("sources", []),
        )

        logger.info(
            "followup_async_generated",
            session_id=session_id,
            count=len(questions),
        )

        return questions

    except Exception as e:
        logger.error(
            "followup_async_generation_error",
            session_id=session_id,
            error=str(e),
        )
        return []


# Export public API
__all__ = [
    "generate_followup_questions",
    "generate_followup_questions_async",
    "store_conversation_context",
    "retrieve_conversation_context",
]
