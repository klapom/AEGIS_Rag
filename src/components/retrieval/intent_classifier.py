"""Intent Classifier for 4-Way Hybrid RRF Retrieval.

Sprint 42 - Feature: Intent-Weighted RRF (TD-057)
Sprint 52 - Feature: Zero-Shot Embedding Classification (Performance Optimization)

This module classifies user queries into one of four intent types:
- factual: Specific fact lookups (e.g., "What is the capital of France?")
- keyword: Keyword-based searches (e.g., "security policy violations 2024")
- exploratory: Broad exploration (e.g., "How does authentication work?")
- summary: High-level overviews (e.g., "Summarize the project architecture")

Classification Methods (Sprint 52):
1. embedding: Zero-Shot Embedding Classification using BGE-M3 (~20-50ms, high accuracy)
2. rule_based: Fast regex pattern matching (~0ms, medium accuracy)
3. llm: LLM-based classification (~2-10s, highest accuracy but slow)

Each intent type has different RRF weight profiles for the 4 retrieval channels:
- Vector (Qdrant): Semantic similarity
- BM25: Keyword matching
- Graph Local: Entity facts (MENTIONED_IN)
- Graph Global: Community/theme context

Academic References:
- Adaptive-RAG (Jeong et al., NAACL 2024) - arXiv:2403.14403
- GraphRAG (Edge et al., 2024) - arXiv:2404.16130
"""

import math
import os
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

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


# Sprint 52: Intent descriptions for Zero-Shot Embedding Classification
# These descriptions are embedded and compared with the query embedding
INTENT_DESCRIPTIONS: dict[Intent, str] = {
    Intent.FACTUAL: (
        "Specific fact lookup question asking who, what, when, where "
        "with a concrete specific answer. Definition or meaning of a term. "
        "Was ist, Wer ist, Wann wurde, Wo befindet sich, Definition von"
    ),
    Intent.KEYWORD: (
        "Technical keyword search with codes, identifiers, error messages, "
        "configuration values, version numbers, file names, API endpoints. "
        "Error 404, JWT token, config.yaml, version 2.3.1, API_KEY"
    ),
    Intent.EXPLORATORY: (
        "Exploration question asking how something works, why something happens, "
        "explain concepts, understand relationships, compare options. "
        "Wie funktioniert, Warum, Erkläre, Unterschied zwischen, Zusammenhang"
    ),
    Intent.SUMMARY: (
        "High-level overview request asking to summarize, give overview, "
        "list main points, provide brief summary, big picture view. "
        "Zusammenfassung, Überblick, Hauptpunkte, Fasse zusammen, Overview"
    ),
}


# Classification prompt for LLM fallback
INTENT_CLASSIFICATION_PROMPT = """Classify this query into one of exactly 4 intent types:
- factual: Specific fact lookup (Who, What, When, Where with a specific answer)
- keyword: Keyword search (technical terms, codes, identifiers, specific phrases)
- exploratory: Exploration (How, Why, explain, understand, relationships)
- summary: Overview request (summarize, overview, main points, high-level)

Query: "{query}"

Respond with ONLY one word: factual, keyword, exploratory, or summary.
Intent:"""


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        vec_a: First vector
        vec_b: Second vector

    Returns:
        Cosine similarity score between -1 and 1
    """
    if len(vec_a) != len(vec_b):
        raise ValueError(f"Vector dimensions must match: {len(vec_a)} vs {len(vec_b)}")

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


class IntentClassifier:
    """Intent Classifier with Zero-Shot Embedding Classification.

    Sprint 52: Replaces slow LLM-based classification with fast embedding-based
    zero-shot classification using BGE-M3 embeddings.

    Classification Methods:
    1. embedding (default): Zero-Shot using BGE-M3 embeddings (~20-50ms)
    2. rule_based: Fast regex patterns (~0ms, fallback)
    3. llm: LLM-based classification (~2-10s, optional)

    Features:
    - Embedding-based zero-shot classification (primary)
    - Rule-based fallback for edge cases
    - Response caching for performance
    - Pre-computed intent embeddings (cached)

    Example:
        classifier = IntentClassifier(method="embedding")
        result = await classifier.classify("What is OMNITRACKER?")
        # result.intent == Intent.FACTUAL
        # result.method == "embedding"
        # result.latency_ms ~= 25.0
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 10.0,
        method: str = "embedding",
    ):
        """Initialize Intent Classifier.

        Args:
            base_url: Ollama API URL (for LLM fallback)
            model: LLM model to use (for LLM fallback)
            timeout: Request timeout in seconds (for LLM fallback)
            method: Classification method: "embedding" (default), "rule_based", or "llm"
        """
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL_INTENT", "nemotron-3-nano")
        self.timeout = timeout
        self.method = method
        self.client = httpx.AsyncClient(timeout=timeout)

        # Cache for query classifications (LRU)
        self._cache: dict[str, tuple[Intent, float]] = {}
        self._cache_max_size = 1000

        # Sprint 52: Cache for intent description embeddings
        self._intent_embeddings: dict[Intent, list[float]] = {}
        self._embeddings_initialized = False

        logger.info(
            "IntentClassifier initialized",
            method=method,
            base_url=self.base_url if method == "llm" else "N/A",
        )

    async def _ensure_intent_embeddings(self) -> None:
        """Initialize intent description embeddings (lazy loading).

        Sprint 52: Pre-computes embeddings for all intent descriptions.
        These are cached and reused for all subsequent classifications.
        """
        if self._embeddings_initialized:
            return

        try:
            from src.components.shared.embedding_service import get_embedding_service

            embedding_service = get_embedding_service()

            init_start = time.perf_counter()

            for intent, description in INTENT_DESCRIPTIONS.items():
                embedding = await embedding_service.embed_single(description)
                self._intent_embeddings[intent] = embedding

            init_time_ms = (time.perf_counter() - init_start) * 1000
            self._embeddings_initialized = True

            logger.info(
                "intent_embeddings_initialized",
                intents_count=len(self._intent_embeddings),
                init_time_ms=round(init_time_ms, 2),
            )

        except Exception as e:
            logger.error("intent_embeddings_init_failed", error=str(e))
            # Don't set initialized - will retry on next call
            raise

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
            cached_intent, cached_time = self._cache[cache_key]
            logger.debug("intent_cache_hit", query=query[:50], intent=cached_intent.value)
            return IntentClassificationResult(
                intent=cached_intent,
                weights=INTENT_WEIGHT_PROFILES[cached_intent],
                confidence=1.0,
                latency_ms=0.0,
                method="cache",
            )

        # Classify based on configured method
        intent: Intent | None = None
        confidence = 0.0
        method = self.method

        if self.method == "embedding":
            try:
                intent, confidence = await self._classify_with_embeddings(query)
                method = "embedding"
            except Exception as e:
                logger.warning(
                    "embedding_classification_failed",
                    query=query[:50],
                    error=str(e),
                    fallback="rule_based",
                )
                intent = None

        elif self.method == "llm":
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

        # Fallback to rule-based if primary method failed or is rule_based
        if intent is None:
            intent = self._classify_rule_based(query)
            confidence = 0.7
            method = "rule_based"

        # Update cache (with LRU eviction)
        if len(self._cache) >= self._cache_max_size:
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

    async def _classify_with_embeddings(self, query: str) -> tuple[Intent, float]:
        """Classify using Zero-Shot Embedding similarity.

        Sprint 52: Uses BGE-M3 embeddings to compute semantic similarity
        between the query and intent descriptions.

        Args:
            query: User query

        Returns:
            Tuple of (Intent, confidence)
        """
        # Ensure intent embeddings are initialized
        await self._ensure_intent_embeddings()

        from src.components.shared.embedding_service import get_embedding_service

        embedding_service = get_embedding_service()

        # Get query embedding
        embed_start = time.perf_counter()
        query_embedding = await embedding_service.embed_single(query)
        embed_time_ms = (time.perf_counter() - embed_start) * 1000

        # Calculate similarity with each intent
        similarities: dict[Intent, float] = {}
        for intent, intent_embedding in self._intent_embeddings.items():
            similarity = cosine_similarity(query_embedding, intent_embedding)
            similarities[intent] = similarity

        # Find best matching intent
        best_intent = max(similarities, key=lambda k: similarities[k])
        best_similarity = similarities[best_intent]

        # Calculate confidence based on margin over second-best
        sorted_sims = sorted(similarities.values(), reverse=True)
        margin = sorted_sims[0] - sorted_sims[1] if len(sorted_sims) > 1 else 0.0
        # Confidence = base similarity + margin bonus (capped at 1.0)
        confidence = min(1.0, (best_similarity + 1) / 2 + margin)

        logger.debug(
            "embedding_classification_complete",
            query=query[:50],
            intent=best_intent.value,
            similarity=round(best_similarity, 4),
            margin=round(margin, 4),
            confidence=round(confidence, 2),
            embed_time_ms=round(embed_time_ms, 2),
            all_similarities={k.value: round(v, 4) for k, v in similarities.items()},
        )

        return best_intent, confidence

    async def _classify_with_llm(self, query: str) -> tuple[Intent, float]:
        """Classify using LLM via Ollama (legacy fallback).

        Args:
            query: User query

        Returns:
            Tuple of (Intent, confidence)
        """
        prompt = INTENT_CLASSIFICATION_PROMPT.format(query=query)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "num_predict": 10,
                "temperature": 0.0,
            },
        }

        response = await self.client.post(
            f"{self.base_url}/api/generate",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        raw_response = data.get("response", "").strip().lower()
        intent = self._parse_intent(raw_response)

        confidence = (
            1.0 if raw_response in ["factual", "keyword", "exploratory", "summary"] else 0.8
        )

        return intent, confidence

    def _parse_intent(self, response: str) -> Intent:
        """Parse LLM response into Intent enum."""
        response = response.strip().lower()

        if response == "factual":
            return Intent.FACTUAL
        if response == "keyword":
            return Intent.KEYWORD
        if response == "exploratory":
            return Intent.EXPLORATORY
        if response == "summary":
            return Intent.SUMMARY

        if "factual" in response:
            return Intent.FACTUAL
        if "keyword" in response:
            return Intent.KEYWORD
        if "exploratory" in response:
            return Intent.EXPLORATORY
        if "summary" in response:
            return Intent.SUMMARY

        logger.warning("intent_parse_fallback", raw_response=response, default="exploratory")
        return Intent.EXPLORATORY

    def _classify_rule_based(self, query: str) -> Intent:
        """Rule-based intent classification fallback.

        Uses heuristics based on query patterns.
        """
        query_lower = query.lower().strip()

        # Summary patterns
        summary_patterns = [
            r"\bsummar",
            r"\boverview\b",
            r"\bmain points\b",
            r"\bhigh[- ]level\b",
            r"\bbrief\b",
            r"\btl;?dr\b",
            r"\bin short\b",
            r"\büberblick\b",
            r"\bzusammenfass",
            r"\bhauptpunkte\b",
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
            r"\bwork\b.*\?",
            r"\bdifference\b",
            r"\bcompare\b",
            r"^wie\b",
            r"^warum\b",
            r"\berklär",
            r"\bunterschied\b",
            r"\bfunktioniert\b",
        ]
        for pattern in exploratory_patterns:
            if re.search(pattern, query_lower):
                return Intent.EXPLORATORY

        # Keyword patterns
        acronym_count = len(re.findall(r"\b[A-Z]{2,}\b", query))
        year_count = len(re.findall(r"\b(19|20)\d{2}\b", query))
        number_count = len(re.findall(r"\b\d{4,}\b", query))
        snake_case_count = len(re.findall(r"\b[a-z]+_[a-z]+\b", query_lower))
        quoted_count = len(re.findall(r'"[^"]+"', query)) + len(re.findall(r"'[^']+'", query))
        technical_terms = sum([
            bool(re.search(r"\berror\b", query_lower)),
            bool(re.search(r"\bcode\b", query_lower)),
            bool(re.search(r"\bconfig\b", query_lower)),
            bool(re.search(r"\bpolicy\b", query_lower)),
            bool(re.search(r"\bviolation\b", query_lower)),
            bool(re.search(r"\btable\b", query_lower)),
            bool(re.search(r"\bschema\b", query_lower)),
            bool(re.search(r"\bdatabase\b", query_lower)),
        ])

        is_short_query = len(query.split()) <= 5
        keyword_indicators = acronym_count + year_count + snake_case_count + quoted_count + technical_terms
        if keyword_indicators >= 2 or acronym_count >= 3 or (is_short_query and number_count >= 1):
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
            r"^was ist\b",
            r"^wer ist\b",
            r"^wann\b",
            r"^wo\b",
            r"^welche\b",
        ]
        for pattern in factual_patterns:
            if re.search(pattern, query_lower):
                return Intent.FACTUAL

        # Default: Exploratory
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
        method: Classification method used (embedding, llm, rule_based, cache)
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

    Sprint 52: Default method is now "embedding" for fast zero-shot classification.

    Returns:
        IntentClassifier instance
    """
    global _intent_classifier
    if _intent_classifier is None:
        # Sprint 52: Use embedding-based classification by default
        method = os.getenv("INTENT_CLASSIFIER_METHOD", "embedding")
        _intent_classifier = IntentClassifier(method=method)
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
        print(f"Method: {result.method}")  # "embedding"
        print(f"Latency: {result.latency_ms}ms")  # ~25ms
    """
    classifier = get_intent_classifier()
    return await classifier.classify(query)
