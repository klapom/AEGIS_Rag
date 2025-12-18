"""Query Router with LLM-based Intent Classification.

This module implements the intelligent query router that classifies user queries
into different intents (VECTOR, GRAPH, HYBRID, MEMORY) using an LLM.

Sprint 4 Feature 4.2: Query Router & Intent Classification
Sprint 48 Feature 48.3: Agent Node Instrumentation (13 SP) - Router
"""

import re
from datetime import datetime
from enum import Enum
from typing import Any

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.components.llm_proxy.aegis_llm_proxy import AegisLLMProxy
from src.components.llm_proxy.models import (
    Complexity,
    LLMTask,
    QualityRequirement,
    TaskType,
)
from src.core.config import settings
from src.models.phase_event import PhaseEvent, PhaseStatus, PhaseType
from src.prompts.router_prompts import CLASSIFICATION_PROMPT

logger = structlog.get_logger(__name__)


class QueryIntent(str, Enum):
    """Query intent classification for routing decisions."""

    VECTOR = "vector"  # Vector search only (semantic similarity)
    GRAPH = "graph"  # Graph traversal only (entity relationships)
    HYBRID = "hybrid"  # Combined vector + graph retrieval
    MEMORY = "memory"  # Temporal memory retrieval
    UNKNOWN = "unknown"  # Unable to classify (fallback to HYBRID)


class IntentClassifier:
    """LLM-based intent classifier using AegisLLMProxy."""

    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        max_retries: int | None = None,
        default_intent: str | None = None,
    ) -> None:
        """Initialize intent classifier.

        Args:
            model_name: LLM model name (default: from settings)
            base_url: DEPRECATED - kept for backward compatibility
            temperature: LLM temperature (default: from settings)
            max_tokens: Max tokens for response (default: from settings)
            max_retries: Max retry attempts (default: from settings)
            default_intent: Default intent on failure (default: from settings)
        """
        self.model_name = model_name or settings.ollama_model_router
        self.temperature = temperature if temperature is not None else settings.router_temperature
        self.max_tokens = max_tokens or settings.router_max_tokens
        self.max_retries = max_retries or settings.router_max_retries
        self.default_intent = default_intent or settings.router_default_intent

        # Initialize AegisLLMProxy for multi-cloud routing
        self.llm_proxy = AegisLLMProxy()

        logger.info(
            "intent_classifier_initialized",
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

    def _parse_intent(self, llm_response: str) -> QueryIntent:
        """Parse intent from LLM response.

        Extracts the intent from the LLM response using pattern matching.
        Handles various response formats and falls back to default if parsing fails.

        Args:
            llm_response: Raw LLM response text

        Returns:
            Parsed QueryIntent enum value
        """
        # Clean up response
        response_clean = llm_response.strip().upper()

        # Try exact match first
        for intent in QueryIntent:
            if intent.value.upper() in response_clean:
                logger.debug("intent_parsed", intent=intent.value, response=llm_response[:100])
                return intent

        # Try pattern matching (e.g., "Intent: VECTOR", "Classification: HYBRID")
        pattern = r"(?:INTENT|CLASSIFICATION|ANSWER):\s*(\w+)"
        match = re.search(pattern, response_clean)
        if match:
            intent_str = match.group(1).lower()
            try:
                intent = QueryIntent(intent_str)
                logger.debug(
                    "intent_parsed_pattern", intent=intent.value, response=llm_response[:100]
                )
                return intent
            except ValueError:
                pass

        # Fallback to default
        logger.warning(
            "intent_parse_failed",
            response=llm_response[:200],
            fallback=self.default_intent,
        )
        return QueryIntent(self.default_intent)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    async def classify_intent(self, query: str) -> QueryIntent:
        """Classify query intent using LLM.

        Uses AegisLLMProxy to classify the query into one of the predefined intents.
        Falls back to default intent on failure after retries.

        Args:
            query: User query string

        Returns:
            Classified QueryIntent enum value

        Raises:
            LLMError: If classification fails after all retries
        """
        try:
            # Format prompt with query
            prompt = CLASSIFICATION_PROMPT.format(query=query)

            logger.debug(
                "classifying_intent",
                query=query[:100],
                model=self.model_name,
            )

            # Create LLM task for intent classification
            task = LLMTask(
                task_type=TaskType.GENERATION,  # Intent classification is a text generation task
                prompt=prompt,
                quality_requirement=QualityRequirement.MEDIUM,
                complexity=Complexity.LOW,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                model_local=self.model_name,  # Prefer local model for fast classification
            )

            # Call AegisLLMProxy
            result = await self.llm_proxy.generate(task)

            # Extract response text
            llm_response = result.content

            # Parse intent
            intent = self._parse_intent(llm_response)

            logger.info(
                "intent_classified",
                query=query[:100],
                intent=intent.value,
                llm_response=llm_response[:100],
                provider=result.provider,
                cost_usd=result.cost_usd,
            )

            return intent

        except Exception as e:
            logger.error(
                "intent_classification_failed",
                query=query[:100],
                error=str(e),
                fallback=self.default_intent,
            )
            # Return default intent instead of raising
            return QueryIntent(self.default_intent)


# Global classifier instance (singleton pattern)
_classifier: IntentClassifier | None = None


def get_classifier() -> IntentClassifier:
    """Get global intent classifier instance (singleton).

    Returns:
        IntentClassifier instance
    """
    global _classifier
    if _classifier is None:
        _classifier = IntentClassifier()
    return _classifier


async def route_query(state: dict[str, Any]) -> dict[str, Any]:
    """Route query node for LangGraph.

    This node classifies the query intent and updates the state.
    It's called by the LangGraph orchestration layer.

    Sprint 48 Feature 48.3: Emits phase events for intent classification.
    Sprint 51 Feature 51.1: Adds phase events to list for streaming.

    Args:
        state: Current agent state

    Returns:
        Updated state with intent field set and phase_event
    """
    query = state.get("query", "")

    logger.info("router_node_processing", query=query[:100])

    # Initialize phase_events list if not present
    if "phase_events" not in state:
        state["phase_events"] = []

    # Create phase event for intent classification
    event = PhaseEvent(
        phase_type=PhaseType.INTENT_CLASSIFICATION,
        status=PhaseStatus.IN_PROGRESS,
        start_time=datetime.utcnow(),
    )

    try:
        # Get classifier
        classifier = get_classifier()

        # Classify intent
        intent = await classifier.classify_intent(query)

        # Update state
        state["intent"] = intent.value
        state["route_decision"] = intent.value

        # Update metadata
        if "metadata" not in state:
            state["metadata"] = {}
        if "agent_path" not in state["metadata"]:
            state["metadata"]["agent_path"] = []

        state["metadata"]["agent_path"].append("router")
        state["metadata"]["intent"] = intent.value

        # Complete phase event successfully
        event.status = PhaseStatus.COMPLETED
        event.end_time = datetime.utcnow()
        event.duration_ms = (event.end_time - event.start_time).total_seconds() * 1000
        event.metadata = {"intent": intent.value}

        # Sprint 51 Feature 51.1: Add to phase_events list
        state["phase_events"].append(event)
        # Also add as phase_event for backward compatibility
        state["phase_event"] = event

        logger.info(
            "router_node_complete",
            query=query[:100],
            intent=intent.value,
            duration_ms=event.duration_ms,
        )

        return state

    except Exception as e:
        logger.error(
            "router_node_error",
            query=query[:100],
            error=str(e),
        )

        # Mark phase event as failed
        event.status = PhaseStatus.FAILED
        event.error = str(e)
        event.end_time = datetime.utcnow()
        event.duration_ms = (event.end_time - event.start_time).total_seconds() * 1000

        # Sprint 51 Feature 51.1: Add to phase_events list
        state["phase_events"].append(event)
        # Also add as phase_event for backward compatibility
        state["phase_event"] = event

        # Set default intent and error
        state["intent"] = settings.router_default_intent
        state["route_decision"] = settings.router_default_intent
        state["error"] = f"Router error: {str(e)}"

        return state


# Export for convenience
__all__ = [
    "QueryIntent",
    "IntentClassifier",
    "get_classifier",
    "route_query",
]
