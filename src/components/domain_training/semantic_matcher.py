"""Semantic Matching for DSPy Evaluation Metrics.

Sprint 45 - Feature 45.17: Embedding-based Matching

This module provides semantic similarity matching for entity and relation
extraction evaluation. Instead of exact string matching, it uses BGE-M3
embeddings to compute cosine similarity, allowing semantically equivalent
but textually different extractions to match.

Key Features:
- Entity matching with configurable similarity threshold
- Relation matching (subject, predicate, object) with weighted similarity
- Caching for embedding computation efficiency
- Fallback to exact matching if embeddings unavailable

Example:
    >>> matcher = SemanticMatcher(threshold=0.7)
    >>> # Exact match would fail, but semantic match succeeds:
    >>> matcher.entities_match("Rechtesystem", "Rechte-System")
    True
    >>> matcher.relations_match(
    ...     {"subject": "OMNITRACKER", "predicate": "verfügt über", "object": "X"},
    ...     {"subject": "OMNITRACKER", "predicate": "hat", "object": "X"}
    ... )
    True
"""

import os
from functools import lru_cache
from typing import Any

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


class SemanticMatcher:
    """Semantic similarity matcher using BGE-M3 embeddings.

    This class provides methods for computing semantic similarity between
    entities and relations using embedding-based cosine similarity.

    Attributes:
        threshold: Minimum similarity score for a match (0.0-1.0)
        predicate_weight: Weight for predicate similarity in relation matching
        _embedder: Lazy-loaded embedding model
    """

    def __init__(
        self,
        threshold: float = 0.75,
        predicate_weight: float = 0.4,
    ) -> None:
        """Initialize semantic matcher.

        Args:
            threshold: Minimum cosine similarity for match (default: 0.75)
            predicate_weight: Weight for predicate in relation similarity.
                Subject and object share remaining weight equally.
                (default: 0.4, so subject=0.3, object=0.3)
        """
        self.threshold = threshold
        self.predicate_weight = predicate_weight
        self._embedder = None
        self._available = None

        logger.info(
            "semantic_matcher_initialized",
            threshold=threshold,
            predicate_weight=predicate_weight,
        )

    @property
    def is_available(self) -> bool:
        """Check if embedding model is available."""
        if self._available is None:
            self._available = self._check_availability()
        return self._available

    def _check_availability(self) -> bool:
        """Check if we can load the embedding model."""
        try:
            from sentence_transformers import SentenceTransformer
            return True
        except ImportError:
            logger.warning(
                "sentence_transformers_not_available",
                fallback="exact_matching",
            )
            return False

    def _get_embedder(self) -> Any:
        """Lazy-load the embedding model."""
        if self._embedder is None:
            if not self.is_available:
                return None

            from sentence_transformers import SentenceTransformer

            # Use BGE-M3 for multilingual support (German documents)
            model_name = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

            logger.info("loading_embedding_model", model=model_name)
            self._embedder = SentenceTransformer(model_name)
            logger.info("embedding_model_loaded", model=model_name)

        return self._embedder

    @lru_cache(maxsize=1000)
    def _get_embedding(self, text: str) -> tuple[float, ...]:
        """Get embedding for text with caching.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as tuple (for hashability)
        """
        embedder = self._get_embedder()
        if embedder is None:
            return tuple()

        embedding = embedder.encode(text, normalize_embeddings=True)
        return tuple(embedding.tolist())

    def cosine_similarity(self, text1: str, text2: str) -> float:
        """Compute cosine similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Cosine similarity score (0.0-1.0), or 1.0 if exact match
        """
        # Fast path: exact match
        if text1.lower().strip() == text2.lower().strip():
            return 1.0

        if not self.is_available:
            # Fallback: simple token overlap
            return self._token_overlap(text1, text2)

        emb1 = self._get_embedding(text1)
        emb2 = self._get_embedding(text2)

        if not emb1 or not emb2:
            return self._token_overlap(text1, text2)

        # Cosine similarity (embeddings are already normalized)
        return float(np.dot(emb1, emb2))

    def _token_overlap(self, text1: str, text2: str) -> float:
        """Simple token overlap as fallback.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Jaccard similarity of tokens
        """
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)

        return intersection / union if union > 0 else 0.0

    def entities_match(self, entity1: str, entity2: str) -> bool:
        """Check if two entities match semantically.

        Args:
            entity1: First entity
            entity2: Second entity

        Returns:
            True if similarity >= threshold
        """
        sim = self.cosine_similarity(entity1, entity2)
        return sim >= self.threshold

    def relations_match(
        self,
        rel1: dict[str, str],
        rel2: dict[str, str],
    ) -> bool:
        """Check if two relations match semantically.

        Computes weighted similarity across subject, predicate, and object.
        Predicate gets higher weight as it's the core relationship.

        Args:
            rel1: First relation {"subject", "predicate", "object"}
            rel2: Second relation {"subject", "predicate", "object"}

        Returns:
            True if weighted similarity >= threshold
        """
        try:
            subj_sim = self.cosine_similarity(rel1["subject"], rel2["subject"])
            pred_sim = self.cosine_similarity(rel1["predicate"], rel2["predicate"])
            obj_sim = self.cosine_similarity(rel1["object"], rel2["object"])
        except KeyError:
            return False

        # Weighted average (predicate is most important)
        other_weight = (1.0 - self.predicate_weight) / 2
        weighted_sim = (
            subj_sim * other_weight +
            pred_sim * self.predicate_weight +
            obj_sim * other_weight
        )

        return weighted_sim >= self.threshold

    def compute_entity_metrics(
        self,
        gold_entities: set[str],
        pred_entities: set[str],
    ) -> dict[str, float]:
        """Compute precision, recall, F1 for entity extraction.

        Uses semantic matching instead of exact set intersection.

        Args:
            gold_entities: Ground truth entities
            pred_entities: Predicted entities

        Returns:
            Dict with precision, recall, f1
        """
        if not gold_entities:
            return {
                "precision": 1.0 if not pred_entities else 0.0,
                "recall": 1.0,
                "f1": 1.0 if not pred_entities else 0.0,
            }

        if not pred_entities:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

        # Count matches using semantic similarity
        tp = 0
        matched_gold = set()
        matched_pred = set()

        for pred in pred_entities:
            for gold in gold_entities:
                if gold in matched_gold:
                    continue
                if self.entities_match(pred, gold):
                    tp += 1
                    matched_gold.add(gold)
                    matched_pred.add(pred)
                    break

        fp = len(pred_entities) - len(matched_pred)
        fn = len(gold_entities) - len(matched_gold)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return {"precision": precision, "recall": recall, "f1": f1}

    def compute_relation_metrics(
        self,
        gold_relations: list[dict[str, str]],
        pred_relations: list[dict[str, str]],
    ) -> dict[str, float]:
        """Compute precision, recall, F1 for relation extraction.

        Uses semantic matching for subject-predicate-object triples.

        Args:
            gold_relations: Ground truth relations
            pred_relations: Predicted relations

        Returns:
            Dict with precision, recall, f1
        """
        if not gold_relations:
            return {
                "precision": 1.0 if not pred_relations else 0.0,
                "recall": 1.0,
                "f1": 1.0 if not pred_relations else 0.0,
            }

        if not pred_relations:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

        # Count matches using semantic similarity
        tp = 0
        matched_gold_indices = set()
        matched_pred_indices = set()

        for pred_idx, pred in enumerate(pred_relations):
            for gold_idx, gold in enumerate(gold_relations):
                if gold_idx in matched_gold_indices:
                    continue
                if self.relations_match(pred, gold):
                    tp += 1
                    matched_gold_indices.add(gold_idx)
                    matched_pred_indices.add(pred_idx)
                    break

        fp = len(pred_relations) - len(matched_pred_indices)
        fn = len(gold_relations) - len(matched_gold_indices)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return {"precision": precision, "recall": recall, "f1": f1}


# Global instance with default settings
_default_matcher: SemanticMatcher | None = None


def get_semantic_matcher(
    threshold: float = 0.75,
    predicate_weight: float = 0.4,
) -> SemanticMatcher:
    """Get or create the default semantic matcher instance.

    Args:
        threshold: Minimum similarity for match
        predicate_weight: Weight for predicate in relation matching

    Returns:
        SemanticMatcher instance
    """
    global _default_matcher

    if _default_matcher is None:
        _default_matcher = SemanticMatcher(
            threshold=threshold,
            predicate_weight=predicate_weight,
        )

    return _default_matcher
