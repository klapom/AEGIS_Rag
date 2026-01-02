"""BM25 Keyword Search Implementation.

This module provides BM25 (Best Matching 25) keyword-based search
as the keyword component of hybrid search.

Sprint 10 Enhancement: Added disk persistence for BM25 index to avoid
re-indexing on every backend restart.

Sprint 70 Feature 70.14: German stopword removal for stronger BM25 signals.
"""

import pickle
from pathlib import Path
from typing import Any

import structlog
from rank_bm25 import BM25Okapi

from src.core.exceptions import VectorSearchError

logger = structlog.get_logger(__name__)

# Sprint 70 Feature 70.14: German stopwords for BM25 preprocessing
# Source: Common German stopwords (articles, prepositions, conjunctions)
# These dilute BM25 term-frequency signals → removed for sharper keyword matching
GERMAN_STOPWORDS = frozenset([
    # Articles
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einer", "eines", "einem", "einen",
    # Pronouns
    "ich", "du", "er", "sie", "es", "wir", "ihr", "mir", "dir", "ihm", "uns", "euch", "ihnen",
    "mein", "dein", "sein", "ihr", "unser", "euer",
    # Prepositions
    "in", "an", "auf", "für", "von", "mit", "zu", "bei", "nach", "über", "unter", "aus", "um",
    "durch", "gegen", "ohne", "hinter", "vor", "neben", "zwischen",
    # Conjunctions
    "und", "oder", "aber", "denn", "sondern", "doch", "jedoch", "sowie", "als", "wenn", "weil",
    "dass", "ob", "bevor", "nachdem", "während", "bis",
    # Common verbs
    "ist", "sind", "war", "waren", "wird", "werden", "wurde", "wurden", "hat", "haben", "hatte",
    "hatten", "sein", "werden", "können", "müssen", "sollen", "wollen", "dürfen", "mögen",
    # Other common words
    "nicht", "auch", "nur", "noch", "schon", "sehr", "wie", "was", "wo", "wann", "warum",
    "welche", "welcher", "welches", "dieser", "diese", "dieses", "jener", "jene", "jenes",
    "alle", "alles", "manche", "mancher", "manches", "einige", "mehrere", "viele", "wenige",
])


class BM25Search:
    """BM25 keyword search for hybrid retrieval with disk persistence."""

    def __init__(self, cache_dir: str = "data/cache") -> None:
        """Initialize BM25 search.

        Args:
            cache_dir: Directory to store BM25 index cache (default: data/cache)
        """
        self._corpus: list[str] = []
        self._metadata: list[dict[str, Any]] = []
        self._bm25: BM25Okapi | None = None
        self._is_fitted = False

        # Setup cache directory
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_file = self._cache_dir / "bm25_index.pkl"

        logger.info("BM25 search initialized", cache_file=str(self._cache_file))

    def _tokenize(self, text: str) -> list[str]:
        """Tokenization with German stopword removal.

        Sprint 70 Feature 70.14: Removes German stopwords to strengthen BM25 signals.
        Vector search keeps stopwords for semantic context.

        Args:
            text: Input text

        Returns:
            list of tokens (stopwords removed, lowercased)

        Example:
            >>> self._tokenize("Was ist ein Knowledge Graph?")
            ['knowledge', 'graph']  # "was", "ist", "ein" removed
        """
        tokens = text.lower().split()
        # Sprint 70.14: Remove German stopwords for sharper BM25 keyword matching
        return [token for token in tokens if token not in GERMAN_STOPWORDS]

    def fit(
        self,
        documents: list[dict[str, Any]],
        text_field: str = "text",
    ) -> None:
        """Fit BM25 model on document corpus.

        Args:
            documents: list of documents with text and metadata
            text_field: Field name containing text (default: "text")

        Raises:
            VectorSearchError: If fitting fails
        """
        try:
            # Extract texts and metadata
            self._corpus = []
            self._metadata = []

            for doc in documents:
                if text_field not in doc:
                    logger.warning(
                        "Document missing text field",
                        text_field=text_field,
                        doc_keys=list(doc.keys()),
                    )
                    continue

                text = doc[text_field]
                self._corpus.append(text)

                # Store metadata (excluding text to save memory)
                metadata = {k: v for k, v in doc.items() if k != text_field}
                self._metadata.append(metadata)

            # Tokenize corpus
            tokenized_corpus = [self._tokenize(doc) for doc in self._corpus]

            # Debug: Check tokenization
            non_empty_docs = sum(1 for tokens in tokenized_corpus if tokens)
            logger.debug(
                "Tokenization complete",
                total_docs=len(tokenized_corpus),
                non_empty_docs=non_empty_docs,
                sample_tokens=(
                    tokenized_corpus[0][:10] if tokenized_corpus and tokenized_corpus[0] else []
                ),
            )

            # Safety check: Ensure we have tokenized content
            if not any(tokenized_corpus):
                raise VectorSearchError(
                    query="",
                    reason=(
                        "All documents resulted in empty tokenization. "
                        "Check that documents have non-empty text content."
                    ),
                )

            # Fit BM25
            self._bm25 = BM25Okapi(tokenized_corpus)
            self._is_fitted = True

            logger.info(
                "BM25 model fitted",
                corpus_size=len(self._corpus),
                non_empty_docs=non_empty_docs,
            )

            # Auto-save to disk after fitting
            self.save_to_disk()

        except Exception as e:
            logger.error("Failed to fit BM25 model", error=str(e))
            raise VectorSearchError(query="", reason=f"Failed to fit BM25 model: {e}") from e

    def search(
        self,
        query: str,
        top_k: int = 10,
        section_filter: str | list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Search documents using BM25.

        Sprint 62 Feature 62.2: Added section_filter parameter.

        Args:
            query: Search query
            top_k: Number of top results to return (default: 10)
            section_filter: Filter by section ID(s) (Sprint 62.2)
                - Single section: "1.2"
                - Multiple sections: ["1.1", "1.2", "2.1"]
                - None: No section filtering (backward compatible)

        Returns:
            list of results with text, score, and metadata

        Raises:
            VectorSearchError: If search fails or model not fitted
        """
        if not self._is_fitted or self._bm25 is None:
            raise VectorSearchError(query=query, reason="BM25 model not fitted. Call fit() first.")

        try:
            # Tokenize query
            tokenized_query = self._tokenize(query)

            # Get BM25 scores
            scores = self._bm25.get_scores(tokenized_query)

            # Sprint 62.2: Apply section filter if provided
            if section_filter is not None:
                # Normalize to list
                section_ids = (
                    [section_filter] if isinstance(section_filter, str) else section_filter
                )

                # Filter results by section_id
                # Set scores to -inf for documents not matching section filter
                for idx, metadata in enumerate(self._metadata):
                    doc_section_id = metadata.get("section_id", "")
                    if doc_section_id not in section_ids:
                        scores[idx] = float("-inf")

                logger.debug(
                    "bm25_section_filter_applied",
                    section_ids=section_ids,
                    num_sections=len(section_ids),
                )

            # Get top-k indices (excluding -inf scores from filtered docs)
            top_indices = scores.argsort()[-top_k:][::-1]

            # Build results (exclude filtered docs with -inf scores)
            results: list[dict[str, Any]] = []
            for idx in top_indices:
                if idx < len(self._corpus) and scores[idx] != float("-inf"):
                    result = {
                        "text": self._corpus[idx],
                        "score": float(scores[idx]),
                        "metadata": self._metadata[idx],
                        "rank": len(results) + 1,
                    }
                    results.append(result)

            logger.debug(
                "BM25 search completed",
                query_length=len(query),
                results_count=len(results),
                top_k=top_k,
                section_filter_applied=section_filter is not None,
            )

            return results

        except Exception as e:
            logger.error("BM25 search failed", error=str(e))
            raise VectorSearchError(query=query, reason=f"BM25 search failed: {e}") from e

    def get_corpus_size(self) -> int:
        """Get size of fitted corpus.

        Returns:
            Number of documents in corpus
        """
        return len(self._corpus)

    def is_fitted(self) -> bool:
        """Check if BM25 model is fitted.

        Returns:
            True if model is fitted
        """
        return self._is_fitted

    def save_to_disk(self) -> None:
        """Save BM25 index to disk for persistence across restarts.

        Sprint 10 Enhancement: Persists the fitted BM25 model to avoid
        re-indexing on every backend restart.

        Raises:
            VectorSearchError: If save fails
        """
        if not self._is_fitted:
            logger.warning("Cannot save unfitted BM25 model")
            return

        try:
            # Save all necessary state
            state = {
                "corpus": self._corpus,
                "metadata": self._metadata,
                "bm25": self._bm25,
                "is_fitted": self._is_fitted,
            }

            with open(self._cache_file, "wb") as f:
                pickle.dump(state, f)

            logger.info(
                "BM25 index saved to disk",
                cache_file=str(self._cache_file),
                corpus_size=len(self._corpus),
            )

        except Exception as e:
            logger.error("Failed to save BM25 index", error=str(e))
            # Non-fatal: model still works in memory
            # raise VectorSearchError(f"Failed to save BM25 index: {e}") from e

    def load_from_disk(self) -> bool:
        """Load BM25 index from disk if it exists.

        Sprint 10 Enhancement: Loads the persisted BM25 model to avoid
        re-indexing on backend restart.

        Returns:
            True if loaded successfully, False if no cache exists

        Raises:
            VectorSearchError: If load fails (but cache exists)
        """
        if not self._cache_file.exists():
            logger.info("No BM25 cache found on disk", cache_file=str(self._cache_file))
            return False

        try:
            with open(self._cache_file, "rb") as f:
                state = pickle.load(f)  # nosec B301 - We control this file

            # Restore state
            self._corpus = state["corpus"]
            self._metadata = state["metadata"]
            self._bm25 = state["bm25"]
            self._is_fitted = state["is_fitted"]

            logger.info(
                "BM25 index loaded from disk",
                cache_file=str(self._cache_file),
                corpus_size=len(self._corpus),
            )
            return True

        except Exception as e:
            logger.error("Failed to load BM25 index from disk", error=str(e))
            raise VectorSearchError(query="", reason=f"Failed to load BM25 index: {e}") from e

    def clear(self) -> None:
        """Clear corpus and reset model."""
        self._corpus.clear()
        self._metadata.clear()
        self._bm25 = None
        self._is_fitted = False
        logger.info("BM25 model cleared")
