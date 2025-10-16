"""Query Router with LLM-based Intent Classification.

This module implements the intelligent query router that classifies user queries
into different intents (VECTOR, GRAPH, HYBRID, MEMORY) using an LLM.

Sprint 4 Feature 4.2: Query Router & Intent Classification
"""

import re
from enum import Enum
from typing import Any

import structlog
from ollama import AsyncClient
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.core.config import settings
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
    """LLM-based intent classifier using Ollama."""

    def __init__(
        self,
        model_name: str | None = None,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        max_retries: int | None = None,
        default_intent: str | None = None,
    ):
        """Initialize intent classifier.

        Args:
            model_name: Ollama model name (default: from settings)
            base_url: Ollama server URL (default: from settings)
            temperature: LLM temperature (default: from settings)
            max_tokens: Max tokens for response (default: from settings)
            max_retries: Max retry attempts (default: from settings)
            default_intent: Default intent on failure (default: from settings)
        """
        self.model_name = model_name or settings.ollama_model_router
        self.base_url = base_url or settings.ollama_base_url
        self.temperature = temperature if temperature is not None else settings.router_temperature
        self.max_tokens = max_tokens or settings.router_max_tokens
        self.max_retries = max_retries or settings.router_max_retries
        self.default_intent = default_intent or settings.router_default_intent

        # Initialize Ollama async client
        self.client = AsyncClient(host=self.base_url)

        logger.info(
            "intent_classifier_initialized",
            model=self.model_name,
            base_url=self.base_url,
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

        Uses Ollama LLM to classify the query into one of the predefined intents.
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

            # Call Ollama LLM
            response = await self.client.generate(
                model=self.model_name,
                prompt=prompt,
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            )

            # Extract response text
            llm_response = response.get("response", "")

            # Parse intent
            intent = self._parse_intent(llm_response)

            logger.info(
                "intent_classified",
                query=query[:100],
                intent=intent.value,
                llm_response=llm_response[:100],
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

    Args:
        state: Current agent state

    Returns:
        Updated state with intent field set
    """
    query = state.get("query", "")

    logger.info("router_node_processing", query=query[:100])

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

        logger.info(
            "router_node_complete",
            query=query[:100],
            intent=intent.value,
        )

        return state

    except Exception as e:
        logger.error(
            "router_node_error",
            query=query[:100],
            error=str(e),
        )

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
