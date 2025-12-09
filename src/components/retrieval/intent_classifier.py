"""Intent Classifier for 4-Way Hybrid RRF Retrieval.

Sprint 42 - Feature: Intent-Weighted RRF (TD-057)

This module classifies user queries into one of four intent types:
- factual: Specific fact lookups (e.g., "What is the capital of France?")
- keyword: Keyword-based searches (e.g., "security policy violations 2024")
- exploratory: Broad exploration (e.g., "How does authentication work?")
- summary: High-level overviews (e.g., "Summarize the project architecture")

Each intent type has different RRF weight profiles for the 4 retrieval channels:
- Vector (Qdrant): Semantic similarity
- BM25: Keyword matching
- Graph Local: Entity facts (MENTIONED_IN)
- Graph Global: Community/theme context

Academic References:
- Adaptive-RAG (Jeong et al., NAACL 2024) - arXiv:2403.14403
- GraphRAG (Edge et al., 2024) - arXiv:2404.16130
"""

import os
import re
import time
from dataclasses import dataclass
from enum import Enum

import httpx
import structlog

logger = structlog.get_logger(__name__)


class Intent(str, Enum):
    """Query intent types for 4-Way Hybrid RRF."""

    FACTUAL = "factual"
    KEYWORD = "keyword"
    EXPLORATORY = "exploratory"
    SUMMARY = "summary"


@dataclass(frozen=True)
class IntentWeights:
    """RRF weights for each retrieval channel based on intent.

    The weights determine how much each retrieval channel contributes
    to the final RRF score:
        score(chunk) = w_vec * 1/(k+r_vec) + w_bm25 * 1/(k+r_bm25)
                     + w_local * 1/(k+r_local) + w_global * 1/(k+r_global)

    Attributes:
        vector: Weight for Qdrant vector search (semantic similarity)
        bm25: Weight for BM25 keyword search
        local: Weight for Graph Local (Entity → Chunk expansion)
        global_: Weight for Graph Global (Community → Entity → Chunk expansion)
    """

    vector: float
    bm25: float
    local: float
    global_: float

    def __post_init__(self) -> None:
        """Validate that weights sum to 1.0."""
        total = self.vector + self.bm25 + self.local + self.global_
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total}")


# Intent → Weight Mappings (from TD-057)
INTENT_WEIGHT_PROFILES: dict[Intent, IntentWeights] = {
    Intent.FACTUAL: IntentWeights(vector=0.3, bm25=0.3, local=0.4, global_=0.0),
    Intent.KEYWORD: IntentWeights(vector=0.1, bm25=0.6, local=0.3, global_=0.0),
    Intent.EXPLORATORY: IntentWeights(vector=0.2, bm25=0.1, local=0.2, global_=0.5),
    Intent.SUMMARY: IntentWeights(vector=0.1, bm25=0.0, local=0.1, global_=0.8),
}


# Classification prompt for qwen3:8b
INTENT_CLASSIFICATION_PROMPT = """Classify this query into one of exactly 4 intent types:
- factual: Specific fact lookup (Who, What, When, Where with a specific answer)
- keyword: Keyword search (technical terms, codes, identifiers, specific phrases)
- exploratory: Exploration (How, Why, explain, understand, relationships)
- summary: Overview request (summarize, overview, main points, high-level)

Query: "{query}"

Respond with ONLY one word: factual, keyword, exploratory, or summary.
Intent:"""


class IntentClassifier:
    """Intent Classifier using qwen3:8b via Ollama.

    This classifier determines the user's query intent to select
    optimal RRF weights for the 4-Way Hybrid Retrieval system.

    Features:
    - LLM-based classification using local qwen3:8b
    - Rule-based fallback if LLM unavailable
    - Response caching for performance
    - Configurable timeout and model

    Example:
        classifier = IntentClassifier()
        result = await classifier.classify("What is the capital of France?")
        # result.intent == Intent.FACTUAL
        # result.weights == IntentWeights(vector=0.3, bm25=0.3, local=0.4, global_=0.0)
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 10.0,
        use_llm: bool = True,
    ):
        """Initialize Intent Classifier.

        Args:
            base_url: Ollama API URL (default: OLLAMA_BASE_URL env or localhost:11434)
            model: Model to use (default: OLLAMA_MODEL_INTENT env or qwen3:8b)
            timeout: Request timeout in seconds (default: 10.0 for fast classification)
            use_llm: Whether to use LLM (True) or rule-based fallback only (False)
        """
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL_INTENT", "qwen3:8b")
        self.timeout = timeout
        self.use_llm = use_llm
        self.client = httpx.AsyncClient(timeout=timeout)

        # Cache for recent classifications (LRU)
        self._cache: dict[str, tuple[Intent, float]] = {}
        self._cache_max_size = 1000

        logger.info(
            "IntentClassifier initialized",
            base_url=self.base_url,
            model=self.model,
            timeout=timeout,
            use_llm=use_llm,
        )

    async def classify(self, query: str) -> "IntentClassificationResult":
        """Classify query intent and return weights.

        Args:
            query: User query string

        Returns:
            IntentClassificationResult with intent, weights, and metadata
        """
        start_time = time.perf_counter()

        # Normalize query for cache lookup
        cache_key = query.lower().strip()

        # Check cache first
        if cache_key in self._cache:
            intent, cached_time = self._cache[cache_key]
            logger.debug("intent_cache_hit", query=query[:50], intent=intent.value)
            return IntentClassificationResult(
                intent=intent,
                weights=INTENT_WEIGHT_PROFILES[intent],
                confidence=1.0,  # Cached results assumed confident
                latency_ms=0.0,
                method="cache",
            )

        # Try LLM classification
        intent: Intent | None = None
        confidence = 0.0
        method = "unknown"

        if self.use_llm:
            try:
                intent, confidence = await self._classify_with_llm(query)
                method = "llm"
            except Exception as e:
                logger.warning(
                    "llm_classification_failed",
                    query=query[:50],
                    error=str(e),
                    fallback="rule_based",
                )
                intent = None

        # Fallback to rule-based if LLM failed or disabled
        if intent is None:
            intent = self._classify_rule_based(query)
            confidence = 0.7  # Rule-based has lower confidence
            method = "rule_based"

        # Update cache (with LRU eviction)
        if len(self._cache) >= self._cache_max_size:
            # Remove oldest entry (first key)
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[cache_key] = (intent, time.time())

        latency_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "intent_classified",
            query=query[:50],
            intent=intent.value,
            confidence=round(confidence, 2),
            method=method,
            latency_ms=round(latency_ms, 2),
        )

        return IntentClassificationResult(
            intent=intent,
            weights=INTENT_WEIGHT_PROFILES[intent],
            confidence=confidence,
            latency_ms=latency_ms,
            method=method,
        )

    async def _classify_with_llm(self, query: str) -> tuple[Intent, float]:
        """Classify using qwen3:8b via Ollama.

        Args:
            query: User query

        Returns:
            Tuple of (Intent, confidence)

        Raises:
            httpx.HTTPStatusError: On API errors
            ValueError: If response cannot be parsed
        """
        prompt = INTENT_CLASSIFICATION_PROMPT.format(query=query)

        # Ollama /api/generate request
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": False,  # Disable Qwen3 thinking mode for fast inference
            "options": {
                "num_predict": 10,  # Only need one word
                "temperature": 0.0,  # Deterministic output
            },
        }

        response = await self.client.post(
            f"{self.base_url}/api/generate",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        raw_response = data.get("response", "").strip().lower()

        # Parse intent from response
        intent = self._parse_intent(raw_response)

        # Confidence based on whether response was clean
        confidence = 1.0 if raw_response in ["factual", "keyword", "exploratory", "summary"] else 0.8

        return intent, confidence

    def _parse_intent(self, response: str) -> Intent:
        """Parse LLM response into Intent enum.

        Args:
            response: LLM response text

        Returns:
            Intent enum value
        """
        response = response.strip().lower()

        # Direct match
        if response == "factual":
            return Intent.FACTUAL
        if response == "keyword":
            return Intent.KEYWORD
        if response == "exploratory":
            return Intent.EXPLORATORY
        if response == "summary":
            return Intent.SUMMARY

        # Partial match (handle "factual." or "Intent: factual")
        if "factual" in response:
            return Intent.FACTUAL
        if "keyword" in response:
            return Intent.KEYWORD
        if "exploratory" in response:
            return Intent.EXPLORATORY
        if "summary" in response:
            return Intent.SUMMARY

        # Default to exploratory (safest middle-ground)
        logger.warning("intent_parse_fallback", raw_response=response, default="exploratory")
        return Intent.EXPLORATORY

    def _classify_rule_based(self, query: str) -> Intent:
        """Rule-based intent classification fallback.

        Uses heuristics based on query patterns:
        - Factual: Who/What/When/Where + specific
        - Keyword: Technical terms, codes, numbers
        - Exploratory: How/Why, explain, understand
        - Summary: Summarize, overview, main points

        Args:
            query: User query

        Returns:
            Intent enum value
        """
        query_lower = query.lower().strip()

        # Summary patterns
        summary_patterns = [
            r"\bsummar",  # summarize, summary
            r"\boverview\b",
            r"\bmain points\b",
            r"\bhigh[- ]level\b",
            r"\bbrief\b",
            r"\btl;?dr\b",
            r"\bin short\b",
        ]
        for pattern in summary_patterns:
            if re.search(pattern, query_lower):
                return Intent.SUMMARY

        # Exploratory patterns
        exploratory_patterns = [
            r"^how\b",
            r"^why\b",
            r"\bexplain\b",
            r"\bunderstand\b",
            r"\brelationship\b",
            r"\bconnect\b",
            r"\bwork\b.*\?",  # "how does X work?"
            r"\bdifference\b",
            r"\bcompare\b",
        ]
        for pattern in exploratory_patterns:
            if re.search(pattern, query_lower):
                return Intent.EXPLORATORY

        # Keyword patterns (technical terms, codes, specific identifiers)
        keyword_patterns = [
            r"\b[A-Z]{2,}\b",  # Acronyms like "API", "JWT", "REST"
            r"\b\d{4,}\b",  # Long numbers (IDs, codes)
            r"\b[a-z]+_[a-z]+\b",  # snake_case identifiers
            r'"[^"]+"',  # Quoted strings
            r"'[^']+'",  # Quoted strings
            r"\berror\b",
            r"\bcode\b",
            r"\bconfig\b",
        ]
        keyword_count = sum(1 for p in keyword_patterns if re.search(p, query_lower))
        if keyword_count >= 2:
            return Intent.KEYWORD

        # Factual patterns
        factual_patterns = [
            r"^what is\b",
            r"^who is\b",
            r"^when\b",
            r"^where\b",
            r"^which\b",
            r"\bdefinition\b",
            r"\bmeaning\b",
        ]
        for pattern in factual_patterns:
            if re.search(pattern, query_lower):
                return Intent.FACTUAL

        # Default: Exploratory (safest for unknown queries)
        return Intent.EXPLORATORY

    async def close(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()

    def clear_cache(self) -> None:
        """Clear the intent classification cache."""
        self._cache.clear()
        logger.info("intent_classifier_cache_cleared")


@dataclass
class IntentClassificationResult:
    """Result of intent classification.

    Attributes:
        intent: Classified intent type
        weights: RRF weights for 4-Way Hybrid Retrieval
        confidence: Classification confidence (0.0-1.0)
        latency_ms: Classification latency in milliseconds
        method: Classification method used (llm, rule_based, cache)
    """

    intent: Intent
    weights: IntentWeights
    confidence: float
    latency_ms: float
    method: str


# Singleton instance
_intent_classifier: IntentClassifier | None = None


def get_intent_classifier() -> IntentClassifier:
    """Get global IntentClassifier instance (singleton).

    Returns:
        IntentClassifier instance
    """
    global _intent_classifier
    if _intent_classifier is None:
        _intent_classifier = IntentClassifier()
    return _intent_classifier


async def classify_intent(query: str) -> IntentClassificationResult:
    """Convenience function to classify query intent.

    Args:
        query: User query string

    Returns:
        IntentClassificationResult with intent, weights, and metadata

    Example:
        result = await classify_intent("What is the project architecture?")
        print(f"Intent: {result.intent.value}")
        print(f"Weights: vec={result.weights.vector}, bm25={result.weights.bm25}")
    """
    classifier = get_intent_classifier()
    return await classifier.classify(query)
