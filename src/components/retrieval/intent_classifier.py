"""Intent Classifier for 4-Way Hybrid RRF Retrieval.

Sprint 42 - Feature: Intent-Weighted RRF (TD-057)
Sprint 52 - Feature: Zero-Shot Embedding Classification (Performance Optimization)
Sprint 67 - Feature 67.12: C-LARA SetFit Integration (TD-075 Phase 3)

This module classifies user queries into one of four intent types:
- factual: Specific fact lookups (e.g., "What is the capital of France?")
- keyword: Keyword-based searches (e.g., "security policy violations 2024")
- exploratory: Broad exploration (e.g., "How does authentication work?")
- summary: High-level overviews (e.g., "Summarize the project architecture")

Classification Methods (Sprint 67):
1. setfit: C-LARA trained SetFit model (~20-50ms, 85-92% accuracy) - NEW
2. embedding: Zero-Shot Embedding Classification using BGE-M3 (~20-50ms, 60% accuracy)
3. rule_based: Fast regex pattern matching (~0ms, medium accuracy)
4. llm: LLM-based classification (~2-10s, highest accuracy but slow)

Each intent type has different RRF weight profiles for the 4 retrieval channels:
- Vector (Qdrant): Semantic similarity
- BM25: Keyword matching
- Graph Local: Entity facts (MENTIONED_IN)
- Graph Global: Community/theme context

Academic References:
- Adaptive-RAG (Jeong et al., NAACL 2024) - arXiv:2403.14403
- GraphRAG (Edge et al., 2024) - arXiv:2404.16130
- C-LARA Framework (Amazon Science) - Intent Detection in the Age of LLMs
"""

import math
import os
import re
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import structlog

if TYPE_CHECKING:
    from setfit import SetFitModel

logger = structlog.get_logger(__name__)


class Intent(str, Enum):
    """Query intent types for 4-Way Hybrid RRF."""

    FACTUAL = "factual"
    KEYWORD = "keyword"
    EXPLORATORY = "exploratory"
    SUMMARY = "summary"


class CLARAIntent(str, Enum):
    """C-LARA intent types from SetFit training (Sprint 81).

    Amazon Science C-LARA Framework:
    - Context-aware LLM-Assisted RAG intent detection
    - 5 classes for fine-grained query routing

    Mapping to IntentWeights (for 4-Way Hybrid RRF):
    - factual → high local graph (entity facts)
    - procedural → high vector + global (how-to guides)
    - comparison → balanced (compare options)
    - recommendation → balanced (suggestions)
    - navigation → high BM25 + local (find documents)
    """

    FACTUAL = "factual"
    PROCEDURAL = "procedural"
    COMPARISON = "comparison"
    RECOMMENDATION = "recommendation"
    NAVIGATION = "navigation"


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


# Intent → Weight Mappings (from TD-057) - Legacy 4-class
INTENT_WEIGHT_PROFILES: dict[Intent, IntentWeights] = {
    Intent.FACTUAL: IntentWeights(vector=0.3, bm25=0.3, local=0.4, global_=0.0),
    Intent.KEYWORD: IntentWeights(vector=0.1, bm25=0.6, local=0.3, global_=0.0),
    Intent.EXPLORATORY: IntentWeights(vector=0.2, bm25=0.1, local=0.2, global_=0.5),
    Intent.SUMMARY: IntentWeights(vector=0.1, bm25=0.0, local=0.1, global_=0.8),
}

# Sprint 81: C-LARA 5-class intent → Weight Mappings (from SetFit training)
# Based on query intent characteristics and retrieval channel strengths
CLARA_INTENT_WEIGHT_PROFILES: dict[CLARAIntent, IntentWeights] = {
    # Factual: Specific facts → high local graph (entity lookup)
    CLARAIntent.FACTUAL: IntentWeights(vector=0.3, bm25=0.3, local=0.4, global_=0.0),
    # Procedural: How-to queries → high vector (semantic) + global (context)
    CLARAIntent.PROCEDURAL: IntentWeights(vector=0.4, bm25=0.1, local=0.2, global_=0.3),
    # Comparison: Compare options → balanced vector + BM25
    CLARAIntent.COMPARISON: IntentWeights(vector=0.35, bm25=0.25, local=0.2, global_=0.2),
    # Recommendation: Suggestions → balanced with slight global preference
    CLARAIntent.RECOMMENDATION: IntentWeights(vector=0.3, bm25=0.2, local=0.2, global_=0.3),
    # Navigation: Find specific docs → high BM25 + local
    CLARAIntent.NAVIGATION: IntentWeights(vector=0.2, bm25=0.5, local=0.3, global_=0.0),
}


# Sprint 52: Intent descriptions for Zero-Shot Embedding Classification
# These descriptions are embedded and compared with the query embedding
INTENT_DESCRIPTIONS: dict[Intent, str] = {
    Intent.FACTUAL: (
        "Specific fact lookup question asking who, what, when, where "
        "with a concrete specific answer. Definition or meaning of a single term. "
        "Exact values, dates, names, locations, specific settings, single entity facts. "
        "Was ist X, Wer ist Y, Wann wurde Z, Wo befindet sich, Definition von, Wert von"
    ),
    Intent.KEYWORD: (
        "Technical keyword search with codes, identifiers, error messages, "
        "configuration values, version numbers, file names, API endpoints. "
        "Error 404, JWT token, config.yaml, version 2.3.1, API_KEY"
    ),
    Intent.EXPLORATORY: (
        "Exploration question asking how something works, why something happens, "
        "explain concepts, understand relationships, compare options, trends, "
        "new features, innovations, developments, what exists, which are available. "
        "Wie funktioniert, Warum, Erkläre, Unterschied zwischen, Zusammenhang, "
        "Trends, Entwicklungen, Innovationen, neue Features, was gibt es, welche"
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

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b, strict=True))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


class IntentClassifier:
    """Intent Classifier with C-LARA SetFit and Zero-Shot Embedding Classification.

    Sprint 52: Embedding-based zero-shot classification using BGE-M3 embeddings
    Sprint 67: C-LARA SetFit model integration for 85-92% accuracy (TD-075)

    Classification Methods:
    1. setfit (Sprint 67): C-LARA trained SetFit model (~20-50ms, 85-92% accuracy)
    2. embedding: Zero-Shot using BGE-M3 embeddings (~20-50ms, 60% accuracy)
    3. rule_based: Fast regex patterns (~0ms, fallback)
    4. llm: LLM-based classification (~2-10s, optional)

    Features:
    - SetFit model with fallback to embedding/rule-based
    - Response caching for performance
    - Feature flag for A/B testing
    - Pre-computed intent embeddings (cached)

    Example:
        classifier = IntentClassifier(method="setfit")
        result = await classifier.classify("What is OMNITRACKER?")
        # result.intent == Intent.FACTUAL
        # result.method == "setfit"
        # result.latency_ms ~= 30.0
        # result.confidence ~= 0.92
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 10.0,
        method: str = "setfit",
        setfit_model_path: str | None = None,
    ):
        """Initialize Intent Classifier.

        Args:
            base_url: Ollama API URL (for LLM fallback)
            model: LLM model to use (for LLM fallback)
            timeout: Request timeout in seconds (for LLM fallback)
            method: Classification method: "setfit" (default), "embedding", "rule_based", or "llm"
            setfit_model_path: Path to SetFit model directory (default: models/intent_classifier)
        """
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_MODEL_INTENT", "nemotron-3-nano")
        self.timeout = timeout
        self.method = method
        self.client = httpx.AsyncClient(timeout=timeout)

        # Sprint 67: SetFit model configuration
        self.setfit_model_path = setfit_model_path or os.getenv(
            "INTENT_CLASSIFIER_MODEL_PATH", "models/intent_classifier"
        )
        self.use_setfit = os.getenv("USE_SETFIT_CLASSIFIER", "true").lower() == "true"
        self.setfit_model: SetFitModel | None = None
        self.setfit_initialized = False

        # Cache for query classifications (LRU)
        self._cache: dict[str, tuple[Intent, float]] = {}
        self._cache_max_size = 1000

        # Sprint 52: Cache for intent description embeddings
        self._intent_embeddings: dict[Intent, list[float]] = {}
        self._embeddings_initialized = False

        logger.info(
            "IntentClassifier initialized",
            method=method,
            use_setfit=self.use_setfit,
            setfit_model_path=self.setfit_model_path,
            base_url=self.base_url if method == "llm" else "N/A",
        )

    def _ensure_setfit_model(self) -> None:
        """Initialize SetFit model (lazy loading).

        Sprint 67: Loads the C-LARA trained SetFit model for intent classification.
        Model is loaded once and cached for subsequent use.
        """
        if self.setfit_initialized:
            return

        if not self.use_setfit:
            logger.info("setfit_model_disabled", reason="USE_SETFIT_CLASSIFIER=false")
            self.setfit_initialized = True
            return

        model_path = Path(self.setfit_model_path)
        if not model_path.exists():
            logger.warning(
                "setfit_model_not_found",
                path=str(model_path),
                fallback="embedding or rule_based",
            )
            self.setfit_initialized = True
            return

        try:
            from setfit import SetFitModel

            init_start = time.perf_counter()
            self.setfit_model = SetFitModel.from_pretrained(str(model_path))
            init_time_ms = (time.perf_counter() - init_start) * 1000

            logger.info(
                "setfit_model_loaded",
                path=str(model_path),
                init_time_ms=round(init_time_ms, 2),
            )
            self.setfit_initialized = True

        except ImportError:
            logger.warning(
                "setfit_not_installed",
                fallback="embedding or rule_based",
                hint="pip install setfit",
            )
            self.setfit_initialized = True
        except Exception as e:
            logger.error("setfit_model_load_failed", error=str(e), path=str(model_path))
            self.setfit_initialized = True

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
                # Sprint 92 Fix: Handle both list (Ollama/ST) and dict (FlagEmbedding) returns
                embedding_result = await embedding_service.embed_single(description)
                embedding = (
                    embedding_result["dense"]
                    if isinstance(embedding_result, dict)
                    else embedding_result
                )
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

    def _classify_with_setfit(self, query: str) -> tuple[CLARAIntent, float]:
        """Classify using C-LARA trained SetFit model.

        Sprint 67: Uses fine-tuned SetFit model for 85-92% accuracy.
        Sprint 81: Updated for 5-class C-LARA intents (95% accuracy).

        Args:
            query: User query

        Returns:
            Tuple of (CLARAIntent, confidence)

        Raises:
            ValueError: If SetFit model is not loaded
        """
        if self.setfit_model is None:
            raise ValueError("SetFit model not loaded")

        # Run prediction
        predict_start = time.perf_counter()
        predictions = self.setfit_model.predict([query])
        predict_time_ms = (time.perf_counter() - predict_start) * 1000

        # Get predicted label - handle both string, int, and tensor predictions
        prediction = predictions[0]

        # Convert tensor to native Python type if needed
        if hasattr(prediction, "item"):
            # PyTorch/NumPy tensor - convert to Python scalar
            prediction = prediction.item()
        elif hasattr(prediction, "numpy"):
            # Tensor without .item() - convert via numpy
            prediction = prediction.numpy().item()

        # Sprint 81: C-LARA 5-class model returns string labels
        if isinstance(prediction, str):
            # Direct string label from SetFit
            label_str = prediction.lower()
            string_to_intent = {
                "factual": CLARAIntent.FACTUAL,
                "procedural": CLARAIntent.PROCEDURAL,
                "comparison": CLARAIntent.COMPARISON,
                "recommendation": CLARAIntent.RECOMMENDATION,
                "navigation": CLARAIntent.NAVIGATION,
            }
            intent = string_to_intent.get(label_str, CLARAIntent.FACTUAL)
        else:
            # Legacy: Integer label (0-4 for C-LARA 5-class)
            predicted_label = int(prediction)
            label_to_intent = {
                0: CLARAIntent.FACTUAL,
                1: CLARAIntent.PROCEDURAL,
                2: CLARAIntent.COMPARISON,
                3: CLARAIntent.RECOMMENDATION,
                4: CLARAIntent.NAVIGATION,
            }
            intent = label_to_intent.get(predicted_label, CLARAIntent.FACTUAL)

        # Get prediction probabilities for confidence
        try:
            probs = self.setfit_model.predict_proba([query])[0]
            # Convert tensor to list/array if needed
            if hasattr(probs, "tolist"):
                probs = probs.tolist()
            elif hasattr(probs, "numpy"):
                probs = probs.numpy().tolist()
            confidence = float(max(probs))

            # Calculate margin (difference between top 2 predictions)
            sorted_probs = sorted(probs, reverse=True)
            margin = sorted_probs[0] - sorted_probs[1] if len(sorted_probs) > 1 else 0.0

            logger.debug(
                "setfit_classification_complete",
                query=query[:50],
                intent=intent.value,
                confidence=round(confidence, 4),
                margin=round(margin, 4),
                predict_time_ms=round(predict_time_ms, 2),
            )

        except AttributeError:
            # Model doesn't support predict_proba, use default confidence
            confidence = 0.85  # Default for SetFit models
            logger.debug(
                "setfit_classification_complete",
                query=query[:50],
                intent=intent.value,
                confidence=confidence,
                predict_time_ms=round(predict_time_ms, 2),
                note="predict_proba not available, using default confidence",
            )

        return intent, confidence

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

        # Check cache first (cache stores tuple of (intent_value, weights, clara_intent_value))
        if cache_key in self._cache:
            cached_data = self._cache[cache_key]
            if len(cached_data) == 3:
                cached_intent_val, cached_weights, cached_clara_val = cached_data
            else:
                # Legacy cache format
                cached_intent, cached_time = cached_data
                cached_intent_val = (
                    cached_intent.value if hasattr(cached_intent, "value") else str(cached_intent)
                )
                cached_weights = INTENT_WEIGHT_PROFILES.get(
                    cached_intent, INTENT_WEIGHT_PROFILES[Intent.FACTUAL]
                )
                cached_clara_val = None

            logger.debug("intent_cache_hit", query=query[:50], intent=cached_intent_val)
            # Reconstruct intent enum
            try:
                legacy_intent = (
                    Intent(cached_intent_val)
                    if cached_intent_val in [e.value for e in Intent]
                    else Intent.FACTUAL
                )
            except ValueError:
                legacy_intent = Intent.FACTUAL

            return IntentClassificationResult(
                intent=legacy_intent,
                weights=cached_weights,
                confidence=1.0,
                latency_ms=0.0,
                method="cache",
                clara_intent=CLARAIntent(cached_clara_val) if cached_clara_val else None,
            )

        # Classify based on configured method
        intent: Intent | None = None
        clara_intent: CLARAIntent | None = None
        weights: IntentWeights | None = None
        confidence = 0.0
        method = self.method

        # Sprint 67/81: Try SetFit first if enabled (returns CLARAIntent)
        if self.method == "setfit":
            try:
                self._ensure_setfit_model()
                if self.setfit_model is not None:
                    clara_intent, confidence = self._classify_with_setfit(query)
                    weights = CLARA_INTENT_WEIGHT_PROFILES[clara_intent]
                    # Map CLARAIntent to legacy Intent for backward compatibility
                    intent = self._clara_to_legacy_intent(clara_intent)
                    method = "setfit"
                else:
                    # SetFit not available, fall through to embedding
                    clara_intent = None
            except Exception as e:
                logger.warning(
                    "setfit_classification_failed",
                    query=query[:50],
                    error=str(e),
                    fallback="embedding or rule_based",
                )
                clara_intent = None

        # Fallback to embedding if setfit failed or method is embedding
        if intent is None and self.method in ["setfit", "embedding"]:
            try:
                intent, confidence = await self._classify_with_embeddings(query)
                weights = INTENT_WEIGHT_PROFILES[intent]
                method = "embedding"
            except Exception as e:
                logger.warning(
                    "embedding_classification_failed",
                    query=query[:50],
                    error=str(e),
                    fallback="rule_based",
                )
                intent = None

        # LLM method
        elif intent is None and self.method == "llm":
            try:
                intent, confidence = await self._classify_with_llm(query)
                weights = INTENT_WEIGHT_PROFILES[intent]
                method = "llm"
            except Exception as e:
                logger.warning(
                    "llm_classification_failed",
                    query=query[:50],
                    error=str(e),
                    fallback="rule_based",
                )
                intent = None

        # Fallback to rule-based if all methods failed or is rule_based
        if intent is None:
            intent = self._classify_rule_based(query)
            weights = INTENT_WEIGHT_PROFILES[intent]
            confidence = 0.7
            method = "rule_based"

        # Update cache (with LRU eviction)
        if len(self._cache) >= self._cache_max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[cache_key] = (
            intent.value,
            weights,
            clara_intent.value if clara_intent else None,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "intent_classified",
            query=query[:50],
            intent=intent.value,
            clara_intent=clara_intent.value if clara_intent else None,
            confidence=round(confidence, 2),
            method=method,
            latency_ms=round(latency_ms, 2),
        )

        return IntentClassificationResult(
            intent=intent,
            weights=weights,
            confidence=confidence,
            latency_ms=latency_ms,
            method=method,
            clara_intent=clara_intent,
        )

    def _clara_to_legacy_intent(self, clara: CLARAIntent) -> Intent:
        """Map C-LARA 5-class intent to legacy 4-class Intent.

        Sprint 81: Provides backward compatibility with existing code.

        Mapping:
        - factual → FACTUAL (direct)
        - procedural → EXPLORATORY (how-to questions)
        - comparison → EXPLORATORY (comparative analysis)
        - recommendation → EXPLORATORY (suggestion queries)
        - navigation → KEYWORD (find specific content)
        """
        mapping = {
            CLARAIntent.FACTUAL: Intent.FACTUAL,
            CLARAIntent.PROCEDURAL: Intent.EXPLORATORY,
            CLARAIntent.COMPARISON: Intent.EXPLORATORY,
            CLARAIntent.RECOMMENDATION: Intent.EXPLORATORY,
            CLARAIntent.NAVIGATION: Intent.KEYWORD,
        }
        return mapping.get(clara, Intent.EXPLORATORY)

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
        # Sprint 92 Fix: Handle both list (Ollama/ST) and dict (FlagEmbedding) returns
        embed_start = time.perf_counter()
        embedding_result = await embedding_service.embed_single(query)
        query_embedding = (
            embedding_result["dense"] if isinstance(embedding_result, dict) else embedding_result
        )
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
        technical_terms = sum(
            [
                bool(re.search(r"\berror\b", query_lower)),
                bool(re.search(r"\bcode\b", query_lower)),
                bool(re.search(r"\bconfig\b", query_lower)),
                bool(re.search(r"\bpolicy\b", query_lower)),
                bool(re.search(r"\bviolation\b", query_lower)),
                bool(re.search(r"\btable\b", query_lower)),
                bool(re.search(r"\bschema\b", query_lower)),
                bool(re.search(r"\bdatabase\b", query_lower)),
            ]
        )

        is_short_query = len(query.split()) <= 5
        keyword_indicators = (
            acronym_count + year_count + snake_case_count + quoted_count + technical_terms
        )
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
        intent: Classified intent type (legacy 4-class)
        weights: RRF weights for 4-Way Hybrid Retrieval
        confidence: Classification confidence (0.0-1.0)
        latency_ms: Classification latency in milliseconds
        method: Classification method used (setfit, embedding, llm, rule_based, cache)
        clara_intent: C-LARA 5-class intent (Sprint 81, None for non-SetFit methods)
    """

    intent: Intent
    weights: IntentWeights
    confidence: float
    latency_ms: float
    method: str
    clara_intent: CLARAIntent | None = None


# Singleton instance
_intent_classifier: IntentClassifier | None = None


def get_intent_classifier() -> IntentClassifier:
    """Get global IntentClassifier instance (singleton).

    Sprint 67: Default method is now "setfit" for C-LARA trained model (85-92% accuracy).
    Falls back to "embedding" if SetFit model not available.

    Returns:
        IntentClassifier instance
    """
    global _intent_classifier
    if _intent_classifier is None:
        # Sprint 67: Use SetFit-based classification by default
        method = os.getenv("INTENT_CLASSIFIER_METHOD", "setfit")
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
        print(f"Method: {result.method}")  # "setfit" (or "embedding" fallback)
        print(f"Latency: {result.latency_ms}ms")  # ~30ms
        print(f"Confidence: {result.confidence}")  # ~0.92
    """
    classifier = get_intent_classifier()
    return await classifier.classify(query)
