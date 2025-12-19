"""Auto-Generated Conversation Titles.

Sprint 35 Feature 35.4: Auto-Generated Conversation Titles

This module provides LLM-based automatic title generation for conversations.
Uses AegisLLMProxy for cost-efficient, multi-cloud title generation.
"""

import structlog

from src.components.llm_proxy import TaskType, get_aegis_llm_proxy
from src.components.llm_proxy.models import Complexity, LLMTask, QualityRequirement

logger = structlog.get_logger(__name__)


async def generate_conversation_title(query: str, answer: str, max_length: int = 5) -> str:
    """Generate a concise 3-5 word title for the conversation.

    Uses AegisLLMProxy with LOW complexity routing (typically local Ollama)
    for cost-efficient title generation.

    Args:
        query: The user's first question
        answer: The assistant's first response
        max_length: Maximum words in title (default 5)

    Returns:
        A concise title string (3-5 words)

    Example:
        >>> title = await generate_conversation_title(
        ...     query="What is retrieval augmented generation?",
        ...     answer="RAG is a technique that combines..."
        ... )
        >>> print(title)
        "Retrieval Augmented Generation Explained"
    """
    # Truncate inputs to avoid token limits
    query_short = query[:200]
    answer_short = answer[:300]

    prompt = f"""Generate a concise title ({max_length} words max) for this conversation.
The title should capture the main topic being discussed.
Do NOT use quotes around the title.
Do NOT include phrases like "Discussion about" or "Question regarding".
Just output the title, nothing else.

User Question: {query_short}
Assistant Answer: {answer_short}

Title:"""

    try:
        llm_proxy = get_aegis_llm_proxy()

        # Create LLM task with LOW complexity (routes to local Ollama = FREE)
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt=prompt,
            quality_requirement=QualityRequirement.LOW,  # Simple task
            complexity=Complexity.LOW,  # Lightweight generation
            max_tokens=20,  # Very short output
            temperature=0.3,  # Low temperature for consistency
            model_local="nemotron-3-nano",  # Sprint 51: Fast Nemotron 3 Nano for titles
        )

        response = await llm_proxy.generate(task)

        # Clean up the title
        title = response.content.strip().strip('"').strip("'")

        # Truncate if too long (more than max_length + 2 words)
        words = title.split()
        if len(words) > max_length + 2:
            title = " ".join(words[:max_length]) + "..."

        logger.info(
            "title_generated",
            title=title,
            provider=response.provider,
            cost_usd=response.cost_usd,
            tokens=response.tokens_used,
        )

        return title or "New Conversation"

    except Exception as e:
        logger.warning("title_generation_failed", error=str(e))
        # Fallback: Use first few words of query
        fallback_title = " ".join(query.split()[:5])
        return fallback_title or "New Conversation"
