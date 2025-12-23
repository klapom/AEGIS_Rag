"""Multi-Turn Agent Nodes.

Sprint 63 Feature 63.1: Multi-Turn RAG Template (13 SP)

This module implements the individual LangGraph nodes for multi-turn conversations:
- Context preparation
- Document search
- Contradiction detection
- Answer generation
- Memory updates
"""

import structlog

from src.agents.multi_turn.state import MultiTurnState
from src.api.models.multi_turn import Contradiction
from src.core.config import settings

logger = structlog.get_logger(__name__)


async def prepare_context_node(state: MultiTurnState) -> dict:
    """Prepare context by summarizing conversation history and enhancing query.

    This node:
    1. Summarizes the last N conversation turns
    2. Extracts key entities and facts
    3. Enhances the current query with historical context
    4. Uses LLM to generate a context-aware query

    Args:
        state: Current multi-turn state

    Returns:
        State update with enhanced_query
    """
    logger.info(
        "prepare_context_start",
        conversation_id=state["conversation_id"],
        current_query=state["current_query"][:100],
        history_length=len(state["conversation_history"]),
    )

    # Get recent conversation history (last max_history_turns)
    max_turns = state.get("max_history_turns", 5)
    recent_history = state["conversation_history"][-max_turns:]

    # If no history, use query as-is
    if not recent_history:
        logger.info("prepare_context_no_history", conversation_id=state["conversation_id"])
        return {"enhanced_query": state["current_query"]}

    # Build context from history
    context_parts = []
    for i, turn in enumerate(recent_history, 1):
        context_parts.append(f"Turn {i}:")
        context_parts.append(f"Q: {turn.query}")
        context_parts.append(f"A: {turn.answer[:200]}...")  # Limit answer length

    conversation_context = "\n".join(context_parts)

    # Use LLM to enhance query with context
    from src.domains.llm_integration.models import LLMTask, QualityRequirement, TaskType
    from src.domains.llm_integration.proxy.aegis_llm_proxy import get_aegis_llm_proxy

    llm_proxy = get_aegis_llm_proxy()

    prompt = f"""You are a helpful assistant that enhances user queries with conversation context.

Given the following conversation history and current query, generate an enhanced query that:
1. Incorporates relevant context from previous turns
2. Makes implicit references explicit
3. Preserves the user's intent
4. Is standalone and doesn't require conversation history to understand

Conversation History:
{conversation_context}

Current Query: {state['current_query']}

Enhanced Query (single line, no explanation):"""

    try:
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt=prompt,
            quality_requirement=QualityRequirement.MEDIUM,
            temperature=0.3,
            max_tokens=200,
        )
        response = await llm_proxy.generate(task)
        enhanced_query = response.content.strip()

        logger.info(
            "prepare_context_complete",
            conversation_id=state["conversation_id"],
            original_query=state["current_query"][:50],
            enhanced_query=enhanced_query[:50],
        )

        return {"enhanced_query": enhanced_query}

    except Exception as e:
        logger.error(
            "prepare_context_failed",
            conversation_id=state["conversation_id"],
            error=str(e),
        )
        # Fallback to original query
        return {"enhanced_query": state["current_query"]}


async def search_node(state: MultiTurnState) -> dict:
    """Search for relevant documents using enhanced query.

    This node:
    1. Uses the enhanced query from context preparation
    2. Searches vector database
    3. Returns top-k relevant documents

    Args:
        state: Current multi-turn state

    Returns:
        State update with current_context
    """
    query = state.get("enhanced_query") or state["current_query"]
    namespace = state.get("namespace", "default")

    logger.info(
        "search_start",
        conversation_id=state["conversation_id"],
        enhanced_query=query[:100],
        namespace=namespace,
    )

    try:
        # Use vector search for retrieval
        from src.components.vector_search.embeddings import get_embedding_service
        from src.components.vector_search.qdrant_client import get_qdrant_client

        qdrant_client = get_qdrant_client()
        embeddings = get_embedding_service()

        # Generate query embedding
        query_vector = await embeddings.embed_query(query)

        # Search with top_k=10
        results = await qdrant_client.async_client.search(
            collection_name=settings.qdrant_collection_name,
            query_vector=query_vector,
            limit=10,
            score_threshold=0.3,
        )

        # Convert results to context format
        contexts = []
        for i, scored_point in enumerate(results):
            payload = scored_point.payload or {}
            contexts.append(
                {
                    "text": payload.get("text", ""),
                    "title": payload.get("title"),
                    "source": payload.get("source"),
                    "score": scored_point.score,
                    "rank": i + 1,
                    "metadata": payload.get("metadata", {}),
                }
            )

        logger.info(
            "search_complete",
            conversation_id=state["conversation_id"],
            results_count=len(contexts),
        )

        return {"current_context": contexts}

    except Exception as e:
        logger.error(
            "search_failed",
            conversation_id=state["conversation_id"],
            error=str(e),
            exc_info=True,
        )
        return {"current_context": []}


async def detect_contradictions_node(state: MultiTurnState) -> dict:
    """Detect contradictions between current and previous answers.

    This node:
    1. Compares current context with previous answers
    2. Uses LLM to identify contradictions
    3. Returns list of contradictions with confidence scores

    Args:
        state: Current multi-turn state

    Returns:
        State update with contradictions
    """
    # Skip if contradiction detection is disabled
    if not state.get("detect_contradictions", True):
        logger.info(
            "detect_contradictions_skipped",
            conversation_id=state["conversation_id"],
        )
        return {"contradictions": []}

    # Skip if no conversation history
    if not state["conversation_history"]:
        return {"contradictions": []}

    logger.info(
        "detect_contradictions_start",
        conversation_id=state["conversation_id"],
        history_length=len(state["conversation_history"]),
    )

    contradictions = []

    # Get recent answers (last 3 turns)
    recent_turns = state["conversation_history"][-3:]

    # Build prompt with current context and previous answers
    current_info_parts = []
    for ctx in state["current_context"][:5]:  # Top 5 contexts
        current_info_parts.append(ctx.get("text", "")[:300])
    current_info = "\n\n".join(current_info_parts)

    previous_answers_parts = []
    for i, turn in enumerate(recent_turns):
        previous_answers_parts.append(f"Turn {i + 1}: {turn.answer[:300]}")
    previous_answers = "\n\n".join(previous_answers_parts)

    from src.domains.llm_integration.models import LLMTask, QualityRequirement, TaskType
    from src.domains.llm_integration.proxy.aegis_llm_proxy import get_aegis_llm_proxy

    llm_proxy = get_aegis_llm_proxy()

    prompt = f"""You are an expert at detecting contradictions in information.

Compare the current information with previous answers and identify any contradictions.

Current Information:
{current_info}

Previous Answers:
{previous_answers}

If there are contradictions, list them in this format:
CONTRADICTION: [brief description]
CURRENT: [conflicting statement from current info]
PREVIOUS: [conflicting statement from previous answer]
TURN: [turn number (1-{len(recent_turns)})]
CONFIDENCE: [0.0-1.0]

If there are no contradictions, respond with: NO CONTRADICTIONS

Response:"""

    try:
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt=prompt,
            quality_requirement=QualityRequirement.MEDIUM,
            temperature=0.1,
            max_tokens=500,
        )
        llm_response = await llm_proxy.generate(task)
        response = llm_response.content

        # Parse response
        if "NO CONTRADICTIONS" in response.upper():
            logger.info(
                "detect_contradictions_none_found",
                conversation_id=state["conversation_id"],
            )
            return {"contradictions": []}

        # Parse contradictions
        lines = response.strip().split("\n")
        current_contradiction = {}

        for line in lines:
            line = line.strip()
            if line.startswith("CONTRADICTION:"):
                if current_contradiction:
                    # Save previous contradiction
                    contradictions.append(
                        Contradiction(
                            current_info=current_contradiction.get("current", ""),
                            previous_info=current_contradiction.get("previous", ""),
                            turn_index=current_contradiction.get("turn", 1) - 1,
                            confidence=current_contradiction.get("confidence", 0.5),
                            explanation=current_contradiction.get("explanation", ""),
                        )
                    )
                current_contradiction = {
                    "explanation": line.split(":", 1)[1].strip(),
                }
            elif line.startswith("CURRENT:"):
                current_contradiction["current"] = line.split(":", 1)[1].strip()
            elif line.startswith("PREVIOUS:"):
                current_contradiction["previous"] = line.split(":", 1)[1].strip()
            elif line.startswith("TURN:"):
                try:
                    current_contradiction["turn"] = int(line.split(":", 1)[1].strip())
                except (ValueError, IndexError):
                    current_contradiction["turn"] = 1
            elif line.startswith("CONFIDENCE:"):
                try:
                    current_contradiction["confidence"] = float(line.split(":", 1)[1].strip())
                except (ValueError, IndexError):
                    current_contradiction["confidence"] = 0.5

        # Add last contradiction
        if current_contradiction:
            contradictions.append(
                Contradiction(
                    current_info=current_contradiction.get("current", ""),
                    previous_info=current_contradiction.get("previous", ""),
                    turn_index=current_contradiction.get("turn", 1) - 1,
                    confidence=current_contradiction.get("confidence", 0.5),
                    explanation=current_contradiction.get("explanation", ""),
                )
            )

        logger.info(
            "detect_contradictions_complete",
            conversation_id=state["conversation_id"],
            contradictions_found=len(contradictions),
        )

        return {"contradictions": contradictions}

    except Exception as e:
        logger.error(
            "detect_contradictions_failed",
            conversation_id=state["conversation_id"],
            error=str(e),
            exc_info=True,
        )
        return {"contradictions": []}


async def answer_node(state: MultiTurnState) -> dict:
    """Generate answer using LLM with retrieved context.

    This node:
    1. Formats retrieved contexts as context string
    2. Includes conversation history if relevant
    3. Generates answer with LLM
    4. Handles contradictions if detected

    Args:
        state: Current multi-turn state

    Returns:
        State update with answer
    """
    logger.info(
        "answer_start",
        conversation_id=state["conversation_id"],
        contexts_count=len(state["current_context"]),
        contradictions_count=len(state["contradictions"]),
    )

    # Format contexts
    context_parts = []
    for i, ctx in enumerate(state["current_context"][:5], 1):
        context_parts.append(f"[{i}] {ctx.get('text', '')[:500]}")
    context_str = "\n\n".join(context_parts)

    # Build prompt
    from src.domains.llm_integration.models import LLMTask, QualityRequirement, TaskType
    from src.domains.llm_integration.proxy.aegis_llm_proxy import get_aegis_llm_proxy

    llm_proxy = get_aegis_llm_proxy()

    query = state["current_query"]

    # Add contradiction warning if any detected
    contradiction_warning = ""
    if state["contradictions"]:
        contradiction_warning = f"\n\nWARNING: {len(state['contradictions'])} contradiction(s) detected between current information and previous answers. Please address these in your response."

    prompt = f"""You are a helpful AI assistant. Answer the user's question based on the provided context.

Context:
{context_str}

{contradiction_warning}

User Question: {query}

Provide a clear, accurate answer based on the context. If the context doesn't contain enough information, say so.

Answer:"""

    try:
        task = LLMTask(
            task_type=TaskType.GENERATION,
            prompt=prompt,
            quality_requirement=QualityRequirement.HIGH,
            temperature=0.7,
            max_tokens=800,
        )
        response = await llm_proxy.generate(task)
        answer = response.content

        logger.info(
            "answer_complete",
            conversation_id=state["conversation_id"],
            answer_length=len(answer),
        )

        return {"answer": answer.strip()}

    except Exception as e:
        logger.error(
            "answer_failed",
            conversation_id=state["conversation_id"],
            error=str(e),
            exc_info=True,
        )
        return {"answer": "I'm sorry, I encountered an error generating the answer."}


async def update_memory_node(state: MultiTurnState) -> dict:
    """Update memory with conversation summary.

    This node:
    1. Checks if turn threshold reached (every 5 turns)
    2. Generates conversation summary with LLM
    3. Stores summary in Graphiti memory
    4. Prunes old turns if needed

    Args:
        state: Current multi-turn state

    Returns:
        State update with memory_summary (if generated)
    """
    logger.info(
        "update_memory_start",
        conversation_id=state["conversation_id"],
        turn_number=state["turn_number"],
    )

    # Generate summary every 5 turns
    if state["turn_number"] % 5 != 0:
        logger.info(
            "update_memory_skipped",
            conversation_id=state["conversation_id"],
            turn_number=state["turn_number"],
        )
        return {}

    # Build conversation text for summarization
    conversation_parts = []
    for turn in state["conversation_history"]:
        conversation_parts.append(f"User: {turn.query}")
        conversation_parts.append(f"Assistant: {turn.answer}")

    conversation_text = "\n".join(conversation_parts)

    from src.domains.llm_integration.models import LLMTask, QualityRequirement, TaskType
    from src.domains.llm_integration.proxy.aegis_llm_proxy import get_aegis_llm_proxy

    llm_proxy = get_aegis_llm_proxy()

    prompt = f"""You are an expert at summarizing conversations.

Summarize the following conversation in 2-3 sentences, capturing:
1. Main topics discussed
2. Key facts or conclusions
3. User's primary interests or questions

Conversation:
{conversation_text}

Summary (2-3 sentences):"""

    try:
        task = LLMTask(
            task_type=TaskType.SUMMARIZATION,
            prompt=prompt,
            quality_requirement=QualityRequirement.MEDIUM,
            temperature=0.3,
            max_tokens=200,
        )
        response = await llm_proxy.generate(task)
        summary = response.content.strip()

        # Store summary in Redis for future context
        from src.components.memory import get_redis_memory

        redis_memory = get_redis_memory()

        await redis_memory.store(
            key=f"{state['conversation_id']}:summary",
            value={"summary": summary, "turn_number": state["turn_number"]},
            namespace="memory",
            ttl_seconds=86400,  # 24 hours
        )

        logger.info(
            "update_memory_complete",
            conversation_id=state["conversation_id"],
            turn_number=state["turn_number"],
            summary_length=len(summary),
        )

        return {"memory_summary": summary}

    except Exception as e:
        logger.error(
            "update_memory_failed",
            conversation_id=state["conversation_id"],
            error=str(e),
            exc_info=True,
        )
        return {}
